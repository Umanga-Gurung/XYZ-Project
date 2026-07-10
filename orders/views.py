from django.shortcuts import render, redirect
from django.contrib import messages
from cart.models import CartItem
from .forms import OrderForm
from .models import Order, OrderProduct, Payment
import datetime
import json
import requests
import hmac
import hashlib
import base64
from django.views.generic import View
from django.urls import reverse
from django.conf import settings
from django.db import transaction
from decimal import Decimal, InvalidOperation


def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body["orderId"])
    payment = Payment(
        user=request.user,
        payment_id=body["transId"],
        payment_method=body["payment_method"],
        amount_paid=order.order_total,
        status=body["status"],
    )
    payment.save()
    order.payment = payment
    order.is_ordered = True
    order.save()

    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = order.id
        orderproduct.user_id = request.user.id
        orderproduct.product_id = item.product_id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()
    CartItem.objects.filter(user=request.user).delete()

    data = {
        "order_number": order.order_number,
        "transId": payment.payment_id,
    }
    return render(request, "orders/payments.html")


def place_order(request, total=0, quantity=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect("order_complete")
    for cart_item in cart_items:
        total += cart_item.product.price * cart_item.quantity
        quantity += cart_item.quantity

    if request.method == "POST":
        data = Order()
        data.user = current_user
        data.first_name = request.POST.get("first_name", "")
        data.last_name = request.POST.get("last_name", "")
        data.phone_number = request.POST.get("phone_number", "")
        data.email = request.POST.get("email", "")
        data.address_line_1 = request.POST.get("address_line_1", "")
        data.address_line_2 = request.POST.get("address_line_2", "")
        data.city = request.POST.get("city", "")
        data.order_note = request.POST.get("order_note", "")
        data.ip = request.META.get("REMOTE_ADDR")
        data.save()
        data.order_total = total
        data.save()

        # Generate a merchant-side order number used as transaction_uuid.
        yr = int(datetime.date.today().strftime("%Y"))
        dt = int(datetime.date.today().strftime("%d"))
        mt = int(datetime.date.today().strftime("%m"))
        d = datetime.date(yr, mt, dt)
        current_date = d.strftime("%Y%m%d")
        import uuid
        order_number = f"{current_date}{data.id}-{uuid.uuid4().hex[:6]}"
        data.order_number = order_number
        data.save()

        return redirect(reverse("esewarequest") + "?o_id=" + str(data.id))

    form = OrderForm()
    return redirect("home")


def order_complete(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by("created_at")
    context = {"orders": orders}
    return render(request, "orders/order_complete.html", context)


class EsewaRequestView(View):
    def get(self, request, *args, **kwargs):
        from django_esewa import EsewaPayment

        o_id = request.GET.get("o_id")
        order = Order.objects.get(id=o_id)

        success_url = request.build_absolute_uri(reverse("esewaverify"))
        failure_url = request.build_absolute_uri(reverse("checkout"))

        total_amount = "{:.2f}".format(float(order.order_total))
        transaction_uuid = str(order.order_number)

        esewa_pay = EsewaPayment(
            product_code=settings.ESEWA_PRODUCT_CODE,
            success_url=success_url,
            failure_url=failure_url,
            secret_key=settings.ESEWA_SECRET_KEY,
            amount=total_amount,
            tax_amount="0.00",
            total_amount=total_amount,
            product_service_charge="0.00",
            product_delivery_charge="0.00",
            transaction_uuid=transaction_uuid
        )
        signature = esewa_pay.create_signature()

        context = {
            "order": order,
            "esewa_payment_url": settings.ESEWA_PAYMENT_URL,
            "esewa_product_code": esewa_pay.product_code,
            "esewa_success_url": esewa_pay.success_url,
            "esewa_failure_url": esewa_pay.failure_url,
            "esewa_amount": esewa_pay.amount,
            "esewa_tax_amount": esewa_pay.tax_amount,
            "esewa_service_charge": esewa_pay.product_service_charge,
            "esewa_delivery_charge": esewa_pay.product_delivery_charge,
            "esewa_total_amount": esewa_pay.total_amount,
            "esewa_transaction_uuid": esewa_pay.transaction_uuid,
            "esewa_signed_field_names": "total_amount,transaction_uuid,product_code",
            "esewa_signature": signature,
        }
        return render(request, "esewarequest.html", context)


class EsewaVerifyView(View):
    def get(self, request, *args, **kwargs):
        from django_esewa import EsewaPayment

        encoded_data = request.GET.get("data")
        if not encoded_data:
            messages.warning(request, "Invalid payment response. Please try again.")
            return redirect("cart")

        try:
            # decode using base64 helper
            response_body_json = base64.b64decode(encoded_data).decode("utf-8")
            response_data = json.loads(response_body_json)
        except Exception:
            messages.warning(request, "Unable to decode payment response.")
            return redirect("cart")

        signed_field_names = response_data.get("signed_field_names", "")
        response_signature = response_data.get("signature", "")
        transaction_uuid = response_data.get("transaction_uuid", "")
        total_amount = response_data.get("total_amount", "")
        product_code = response_data.get("product_code", "")
        response_status = response_data.get("status", "")

        if not all([signed_field_names, response_signature, transaction_uuid, total_amount, product_code]):
            messages.warning(request, "Incomplete payment response from eSewa.")
            return redirect("cart")

        if product_code != settings.ESEWA_PRODUCT_CODE:
            messages.warning(request, "Invalid product code in payment response.")
            return redirect("cart")

        # Verify using EsewaPayment
        try:
            esewa_pay = EsewaPayment(
                product_code=settings.ESEWA_PRODUCT_CODE,
                secret_key=settings.ESEWA_SECRET_KEY,
                total_amount=total_amount,
                transaction_uuid=transaction_uuid
            )
            esewa_pay.create_signature()
            is_valid, _ = esewa_pay.verify_signature(encoded_data)
        except Exception:
            is_valid = False

        if not is_valid:
            messages.warning(request, "Invalid payment signature. Please try again.")
            return redirect("cart")

        if response_status != "COMPLETE":
            messages.warning(request, "Payment was not completed.")
            return redirect("cart")

        try:
            order_obj = Order.objects.get(order_number=transaction_uuid, is_ordered=False)
        except Order.DoesNotExist:
            messages.warning(request, "Order not found or already processed.")
            return redirect("cart")

        try:
            expected_amount = Decimal(str(order_obj.order_total))
            received_amount = Decimal(str(total_amount))
        except (InvalidOperation, TypeError, ValueError):
            order_obj.delete()
            messages.warning(request, "Invalid payment amount received. Please try again.")
            return redirect("cart")

        if expected_amount != received_amount:
            order_obj.delete()
            messages.warning(request, "Payment amount did not match the order total.")
            return redirect("cart")

        # Check transaction status on eSewa servers
        is_sandbox = "rc.esewa.com.np" in settings.ESEWA_STATUS_CHECK_URL
        try:
            status_completed = esewa_pay.is_completed(dev=is_sandbox)
        except Exception:
            messages.warning(request, "Unable to verify payment status with eSewa.")
            return redirect("cart")

        if not status_completed:
            order_obj.delete()
            messages.warning(request, "Payment failed. Please try again.")
            return redirect("cart")

        user = order_obj.user
        if not user:
            order_obj.delete()
            messages.warning(request, "Order is missing a user. Please try again.")
            return redirect("cart")

        ref_id = response_data.get("transaction_code")
        with transaction.atomic():
            payment = Payment.objects.create(
                user=user,
                payment_id=ref_id or transaction_uuid,
                payment_method="Esewa",
                amount_paid=str(received_amount),
                status="COMPLETE",
            )
            order_obj.payment = payment
            order_obj.is_ordered = True
            order_obj.status = "Completed"
            order_obj.save()

            cart_items = CartItem.objects.filter(user=user)
            for item in cart_items:
                OrderProduct.objects.create(
                    order=order_obj,
                    user=user,
                    product=item.product,
                    quantity=item.quantity,
                    product_price=item.product.price,
                    ordered=True,
                )

            cart_items.delete()

        return redirect("order_complete")
