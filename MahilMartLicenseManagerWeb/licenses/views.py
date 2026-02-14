from datetime import datetime, timezone as datetime_timezone

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import GeneratedLicense, LicenseRuntimeConfig
from .services import (
    calculate_license_valid_until,
    generate_machine_license_key,
    fetch_recent_mongo_licenses,
    get_license_key_validity_minutes,
    get_runtime_mongo_config,
    is_browser_style_machine_id,
    is_machine_id_valid,
    normalize_machine_id,
    save_shared_mongo_config,
    sync_to_mongo,
)


def _save_license_for_machine(
    *,
    machine_id,
    license_key,
    customer_name,
    contact_email,
    note,
    generated_by,
    source,
    generated_at,
    valid_until,
):
    existing_records = GeneratedLicense.objects.filter(machine_id=machine_id).order_by(
        "-generated_at", "-id"
    )
    primary_record = existing_records.first()

    if primary_record is None:
        return GeneratedLicense.objects.create(
            machine_id=machine_id,
            license_key=license_key,
            customer_name=customer_name,
            contact_email=contact_email,
            note=note,
            generated_by=generated_by,
            status="valid",
            source=source,
            valid_until=valid_until,
        )

    primary_record.license_key = license_key
    primary_record.customer_name = customer_name
    primary_record.contact_email = contact_email
    primary_record.note = note
    primary_record.generated_by = generated_by
    primary_record.status = "valid"
    primary_record.source = source
    primary_record.generated_at = generated_at
    primary_record.valid_until = valid_until
    primary_record.save()

    existing_records.exclude(pk=primary_record.pk).delete()
    return primary_record


def _branding_context():
    return {
        "app_name": "MahilMart License Manager",
        "app_short": "MMLM",
        "app_tagline": "License Control Center",
        "app_version": "v1.0.0",
    }


def _role_value(user):
    if user.is_superuser:
        return "admin"
    if user.is_staff:
        return "supervisor"
    return "cashier"


def _apply_role(user, role):
    user.is_superuser = role == "admin"
    user.is_staff = role in {"admin", "supervisor"}


def _is_superuser(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def _record_value(item, key):
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _record_local_date(value):
    if value is None:
        return None
    if timezone.is_naive(value):
        value = value.replace(tzinfo=datetime_timezone.utc)
    return timezone.localtime(value).date()


def _record_local_datetime(value):
    if value is None:
        return None
    if timezone.is_naive(value):
        value = value.replace(tzinfo=datetime_timezone.utc)
    return timezone.localtime(value)


def _record_set(item, key, value):
    if isinstance(item, dict):
        item[key] = value
    else:
        setattr(item, key, value)


def _merge_recent_licenses(local_items, mongo_items, limit=100):
    minimum_dt = datetime.min.replace(tzinfo=datetime_timezone.utc)
    merged = list(local_items) + list(mongo_items)

    merged.sort(
        key=lambda item: _record_local_datetime(_record_value(item, "generated_at")) or minimum_dt,
        reverse=True,
    )

    deduped = []
    seen_keys = set()
    for item in merged:
        license_key = (_record_value(item, "license_key") or "").strip()
        if license_key and license_key in seen_keys:
            continue
        if license_key:
            seen_keys.add(license_key)
        deduped.append(item)
        if len(deduped) >= max(1, int(limit)):
            break

    return deduped


def login_view(request):
    if not User.objects.filter(is_superuser=True).exists():
        return redirect("licenses:initial_admin_setup")

    # Always require fresh login when user lands on the login route.
    if request.user.is_authenticated:
        logout(request)

    context = _branding_context()
    context.update({"error": "", "username": ""})

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        context["username"] = username

        user = authenticate(request, username=username, password=password)
        if user is None:
            context["error"] = "Invalid username or password."
            return render(request, "licenses/home.html", context)

        if not user.is_active:
            context["error"] = "This user account is inactive."
            return render(request, "licenses/home.html", context)

        login(request, user)
        return redirect("licenses:dashboard")

    return render(request, "licenses/home.html", context)


def healthz_view(request):
    response = JsonResponse(
        {
            "status": "ok",
            "app": "MahilMartLicenseManagerWeb",
        }
    )
    response["Access-Control-Allow-Origin"] = "*"
    response["Cache-Control"] = "no-store"
    return response


def initial_admin_setup(request):
    if User.objects.filter(is_superuser=True).exists():
        return redirect("licenses:login")

    context = _branding_context()
    context.update(
        {
            "errors": [],
            "form": {
                "username": "",
                "email": "",
            },
        }
    )

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        confirm_password = request.POST.get("confirm_password") or ""

        context["form"]["username"] = username
        context["form"]["email"] = email

        if not username:
            context["errors"].append("Username is required.")
        if username and User.objects.filter(username__iexact=username).exists():
            context["errors"].append("Username already exists.")

        if not password:
            context["errors"].append("Password is required.")
        elif len(password) < 6:
            context["errors"].append("Password must be at least 6 characters.")

        if password != confirm_password:
            context["errors"].append("Passwords do not match.")

        if not context["errors"]:
            User.objects.create_superuser(username=username, email=email, password=password)
            messages.success(request, "Superuser created successfully. Please login.")
            return redirect("licenses:login")

    return render(request, "licenses/admin_setup.html", context)


@login_required(login_url="licenses:login")
def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "Logged out successfully.")
        return redirect("licenses:login")
    return redirect("licenses:dashboard")


@login_required(login_url="licenses:login")
def dashboard_view(request):
    generated_key = ""
    generated_machine = "-"
    form_values = {
        "machine_id": "",
        "customer_name": "",
        "contact_email": "",
        "note": "",
    }
    mongo_form_values = get_runtime_mongo_config()

    if request.method == "POST":
        form_action = (request.POST.get("form_action") or "generate_license").strip()

        if form_action == "save_mongo_settings":
            if not request.user.is_superuser:
                messages.error(request, "Only admin can change MongoDB settings.")
            else:
                mongo_uri = (request.POST.get("mongo_uri") or "").strip()
                mongo_db = (request.POST.get("mongo_db") or "").strip()
                mongo_collection = (request.POST.get("mongo_collection") or "").strip()

                mongo_form_values = {
                    "mongo_uri": mongo_uri,
                    "mongo_db": mongo_db,
                    "mongo_collection": mongo_collection,
                }

                if not mongo_db or not mongo_collection:
                    messages.error(request, "Mongo DB and Collection are required.")
                else:
                    LicenseRuntimeConfig.save_singleton(
                        mongo_uri=mongo_uri,
                        mongo_db=mongo_db,
                        mongo_collection=mongo_collection,
                        updated_by=request.user.username,
                    )
                    shared_saved, shared_message = save_shared_mongo_config(
                        mongo_uri=mongo_uri,
                        mongo_db=mongo_db,
                        mongo_collection=mongo_collection,
                    )
                    mongo_form_values = get_runtime_mongo_config()
                    messages.success(request, "MongoDB settings updated successfully.")
                    if not shared_saved:
                        messages.warning(request, shared_message)
        else:
            machine_id = normalize_machine_id(request.POST.get("machine_id"))
            customer_name = (request.POST.get("customer_name") or "").strip()
            contact_email = (request.POST.get("contact_email") or "").strip().lower()
            note = (request.POST.get("note") or "").strip()

            form_values.update(
                {
                    "machine_id": machine_id,
                    "customer_name": customer_name,
                    "contact_email": contact_email,
                    "note": note,
                }
            )

            if not is_machine_id_valid(machine_id):
                messages.error(
                    request,
                    "Enter valid Machine ID (3-64 chars: letters, numbers, dot, underscore, hyphen).",
                )
            elif is_browser_style_machine_id(machine_id):
                messages.error(
                    request,
                    "POS browser UUID not allowed. Use installer machine ID (example: DESKTOP-XXXXXXX).",
                )
            else:
                generated_at = timezone.now()
                valid_until = calculate_license_valid_until(generated_at)
                generated_key = generate_machine_license_key(machine_id, generated_at=generated_at)
                generated_machine = machine_id
                generated_by = request.user.username
                source_name = settings.LICENSE_SOURCE

                _save_license_for_machine(
                    machine_id=machine_id,
                    license_key=generated_key,
                    customer_name=customer_name,
                    contact_email=contact_email,
                    note=note,
                    generated_by=generated_by,
                    source=source_name,
                    generated_at=generated_at,
                    valid_until=valid_until,
                )

                synced, sync_message = sync_to_mongo(
                    {
                        "license_key": generated_key,
                        "machine_id": machine_id,
                        "customer_name": customer_name,
                        "contact_email": contact_email,
                        "note": note,
                        "generated_by": generated_by,
                        "status": "valid",
                        "source": source_name,
                        "generated_at": generated_at,
                        "valid_until": valid_until,
                    }
                )
                valid_until_text = timezone.localtime(valid_until).strftime("%Y-%m-%d %H:%M:%S")
                validity_minutes = get_license_key_validity_minutes()
                messages.success(
                    request,
                    f"License generated: {generated_key} (valid for {validity_minutes} minutes, until {valid_until_text}).",
                )
                if not synced:
                    messages.warning(request, sync_message)

    local_licenses = list(GeneratedLicense.objects.all()[:100])
    mongo_licenses = fetch_recent_mongo_licenses(limit=100)
    recent_licenses = _merge_recent_licenses(local_licenses, mongo_licenses, limit=100)
    now_local = timezone.localtime()
    for item in recent_licenses:
        generated_at = _record_value(item, "generated_at")
        valid_until = _record_value(item, "valid_until")
        if valid_until is None and generated_at is not None:
            valid_until = calculate_license_valid_until(generated_at)

        valid_until_local = _record_local_datetime(valid_until) if valid_until is not None else None
        is_valid = bool(valid_until_local and valid_until_local >= now_local)

        _record_set(item, "valid_until", valid_until_local)
        _record_set(item, "status", "valid" if is_valid else "expired")

    total_keys = len(recent_licenses)
    today = timezone.localtime().date()
    today_keys = sum(1 for item in recent_licenses if _record_local_date(_record_value(item, "generated_at")) == today)
    unique_machines = len({_record_value(item, "machine_id") for item in recent_licenses if _record_value(item, "machine_id")})
    last_generated = _record_value(recent_licenses[0], "generated_at") if recent_licenses else None

    context = {
        "license_email": settings.LICENSE_EMAIL,
        "generated_key": generated_key,
        "generated_machine": generated_machine,
        "recent_licenses": recent_licenses,
        "total_keys": total_keys,
        "today_keys": today_keys,
        "unique_machines": unique_machines,
        "last_generated": last_generated,
        "form_values": form_values,
        "mongo_form_values": mongo_form_values,
    }
    return render(request, "licenses/dashboard.html", context)


@login_required(login_url="licenses:login")
@user_passes_test(_is_superuser, login_url="licenses:dashboard")
def user_list_view(request):
    query = (request.GET.get("q") or "").strip()
    users = User.objects.all().order_by("id")

    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query))

    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "query": query,
        "page_obj": page_obj,
        "total_users": users.count(),
    }
    return render(request, "licenses/user_list.html", context)


@login_required(login_url="licenses:login")
@user_passes_test(_is_superuser, login_url="licenses:dashboard")
def user_create_view(request):
    role_options = {"cashier", "supervisor", "admin"}
    context = {
        "mode": "create",
        "title": "Create User",
        "submit_label": "Create User",
        "errors": [],
        "form": {
            "username": "",
            "email": "",
            "role": "cashier",
            "is_active": True,
        },
    }

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        confirm_password = request.POST.get("confirm_password") or ""
        role = (request.POST.get("role") or "cashier").strip().lower()
        is_active = request.POST.get("is_active") == "on"

        context["form"].update(
            {
                "username": username,
                "email": email,
                "role": role,
                "is_active": is_active,
            }
        )

        if not username:
            context["errors"].append("Username is required.")
        if username and User.objects.filter(username__iexact=username).exists():
            context["errors"].append("Username already exists.")

        if not password:
            context["errors"].append("Password is required.")
        elif len(password) < 6:
            context["errors"].append("Password must be at least 6 characters.")

        if password != confirm_password:
            context["errors"].append("Passwords do not match.")

        if role not in role_options:
            context["errors"].append("Select a valid role.")

        if not context["errors"]:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=is_active,
            )
            _apply_role(user, role)
            user.save()

            messages.success(request, f"User '{username}' created successfully.")
            return redirect("licenses:user_list")

    return render(request, "licenses/user_form.html", context)


@login_required(login_url="licenses:login")
@user_passes_test(_is_superuser, login_url="licenses:dashboard")
def user_edit_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id)

    context = {
        "mode": "edit",
        "title": f"Edit User: {target_user.username}",
        "submit_label": "Save Changes",
        "errors": [],
        "editing_user": target_user,
        "form": {
            "username": target_user.username,
            "email": target_user.email or "",
            "role": _role_value(target_user),
            "is_active": bool(target_user.is_active),
        },
    }

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        confirm_password = request.POST.get("confirm_password") or ""
        role = (request.POST.get("role") or "cashier").strip().lower()
        is_active = request.POST.get("is_active") == "on"

        context["form"].update(
            {
                "username": username,
                "email": email,
                "role": role,
                "is_active": is_active,
            }
        )

        if not username:
            context["errors"].append("Username is required.")
        if (
            username
            and User.objects.filter(username__iexact=username)
            .exclude(id=target_user.id)
            .exists()
        ):
            context["errors"].append("Username already exists.")

        if role not in {"cashier", "supervisor", "admin"}:
            context["errors"].append("Select a valid role.")

        if password or confirm_password:
            if len(password) < 6:
                context["errors"].append("Password must be at least 6 characters.")
            if password != confirm_password:
                context["errors"].append("Passwords do not match.")

        if target_user.is_superuser and role != "admin":
            other_superusers = User.objects.filter(is_superuser=True).exclude(id=target_user.id)
            if not other_superusers.exists():
                context["errors"].append("At least one superuser must remain in the system.")

        if target_user.is_superuser and not is_active:
            other_superusers = User.objects.filter(is_superuser=True).exclude(id=target_user.id)
            if not other_superusers.exists():
                context["errors"].append("The last superuser cannot be deactivated.")

        if not context["errors"]:
            target_user.username = username
            target_user.email = email
            target_user.is_active = is_active
            _apply_role(target_user, role)

            password_changed = bool(password)
            if password_changed:
                target_user.set_password(password)

            target_user.save()

            if password_changed and target_user.id == request.user.id:
                update_session_auth_hash(request, target_user)

            messages.success(request, f"User '{target_user.username}' updated successfully.")
            return redirect("licenses:user_list")

    return render(request, "licenses/user_form.html", context)
