from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from decimal import Decimal, DecimalException, InvalidOperation
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files import File
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from datetime import timedelta
from django.db.models import Sum, Count
import csv
from .models import Customer, Loan, GoldItem, GoldItemImage, GoldItemBundle, LoanDocument, Payment, LoanExpense, LoanPledge, LoanPledgeAdjustment


def get_loan_session(request):
    return request.session.setdefault("loan_entry", {})

def home(request):
    from datetime import date, timedelta
    
    # 1. Loan Status Distribution Data
    active_loans_count = Loan.objects.filter(status=Loan.STATUS_ACTIVE).count()
    closed_loans_count = Loan.objects.filter(status=Loan.STATUS_CLOSED).count()
    # Assuming 'extended' is tracked via parent_loan being set, not a status field value 'extended'
    extended_loans_count = Loan.objects.filter(parent_loan__isnull=False).count()
    
    loans_by_status = {
        'active': active_loans_count,
        'closed': closed_loans_count,
        'extended': extended_loans_count
    }
    
    status_chart_data = {
        'labels': ['Active', 'Closed', 'Extended'],
        'data': [
            loans_by_status.get('active', 0),
            loans_by_status.get('closed', 0),
            loans_by_status.get('extended', 0)
        ]
    }
    
    # 2. Daily Loan Creation Trend (Last 30 days)
    today = date.today()
    daily_trends = []
    
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        count = Loan.objects.filter(created_at__date=day).count()
        daily_trends.append({
            'date': day.strftime('%b %d'),
            'count': count
        })
        
    daily_chart_data = {
        'labels': [item['date'] for item in daily_trends],
        'data': [item['count'] for item in daily_trends]
    }

    context = {
        'status_chart_data': status_chart_data,
        'daily_chart_data': daily_chart_data,
    }
    
    return render(request, "gold_loan/home.html", context)


def dashboard(request):
    sort_param = request.GET.get("sort", "date_desc")
    status_param = request.GET.get("status", "active")
    
    loans = Loan.objects.select_related('customer').prefetch_related('extensions')
    
    # Apply Status Filter
    if status_param == "active":
        loans = loans.filter(status=Loan.STATUS_ACTIVE)
    elif status_param == "closed":
        # Closed but NOT extended
        loans = loans.filter(status=Loan.STATUS_CLOSED, extensions__isnull=True)
    elif status_param == "extended":
        # Loans that have been extended (are parents to other loans)
        loans = loans.filter(extensions__isnull=False)
    elif status_param == "all":
        # No filter
        pass

    # Apply Sorting
    if sort_param == "date_asc":
        loans = loans.order_by("created_at")
    elif sort_param == "name_asc":
        loans = loans.order_by("customer__name")
    elif sort_param == "name_desc":
        loans = loans.order_by("-customer__name")
    else: # Default: date_desc
        loans = loans.order_by("-created_at")

    context = {
        "loans": loans,
        "current_sort": sort_param,
        "current_status": status_param
    }
    return render(request, "gold_loan/dashboard/dashboard.html", context)


# Redirect /loan/ → Step 1
def loan_entry(request):
    if "loan_entry" in request.session:
        del request.session["loan_entry"]
    return redirect("gold_loan:loan_entry_step1")


def payment(request):
    # Redirect legacy /payment/ access to dashboard as payment now requires a specific loan
    return redirect("gold_loan:dashboard")


def closed_loans_list(request):
    loans = Loan.objects.filter(status=Loan.STATUS_CLOSED).select_related("customer").order_by("-closed_at")
    context = {
        "loans": loans,
        "title": "Closed Loans"
    }
    return render(request, "gold_loan/loan/loan_list.html", context)


def extended_loans_list(request):
    # Loans that were created as extensions (have a parent_loan)
    loans = Loan.objects.filter(parent_loan__isnull=False).select_related("customer", "parent_loan").order_by("-created_at")
    context = {
        "loans": loans,
        "title": "Extended Loans"
    }
    return render(request, "gold_loan/loan/loan_list.html", context)


def loan_close(request):
    # This was a placeholder, now we should probably use a loan-specific close view
    # But since we are likely calling this with a loan ID: loan/<id>/close/ ?
    # The URL pattern provided in earlier steps was: path("close/", views.loan_close, name="loan_close") 
    # which is generic and likely wrong for a specific loan. 
    # We should add a new view `loan_close_action` or specific `loan_close_confirm`.
    # Let's keep this as a redirect or error for safety if accessed directly.
    return redirect("gold_loan:dashboard")


def loan_close_action(request, loan_id):
    """
    Step 1: Check if loan is eligible for closure.
    """
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Update interest to be accurate
    _update_loan_interest(loan)
    
    outstanding_principal = _calculate_outstanding_principal(loan)
    pending_interest = loan.pending_interest
    total_due = outstanding_principal + pending_interest
    
    can_close = total_due <= 0
    
    context = {
        "loan": loan,
        "outstanding_principal": outstanding_principal,
        "pending_interest": pending_interest,
        "total_due": total_due,
        "can_close": can_close
    }
    # Using 'loan_close_check.html' as requested (renaming in concept, will create file)
    return render(request, "gold_loan/closure/loan_close_check.html", context)


def loan_close_otp(request, loan_id):
    """
    Step 2: OTP Verification
    """
    loan = get_object_or_404(Loan, id=loan_id)
    next_action = request.GET.get("action", "close")
    
    if request.method == "POST":
        otp = request.POST.get("otp")
        next_action = request.POST.get("next_action", "close") # Preserve from form

        if otp == "123456": # Mock OTP
            # Set session flag
            request.session['loan_closure_verified_id'] = loan.id
            request.session['loan_closure_next_action'] = next_action
            return redirect("gold_loan:loan_close_upload", loan_id=loan.id)
        else:
            return render(request, "gold_loan/closure/loan_close_otp.html", {
                "loan": loan,
                "error": "Invalid OTP. Please try again.",
                "next_action": next_action
            })
            
    # GET: Send/Generate OTP
    return render(request, "gold_loan/closure/loan_close_otp.html", {
        "loan": loan,
        "next_action": next_action
    })


def loan_close_upload(request, loan_id):
    """
    Step 3: Upload Closure Receipts
    """
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Security check: must have passed OTP
    if request.session.get('loan_closure_verified_id') != loan.id:
         return redirect("gold_loan:loan_close_otp", loan_id=loan.id)
         
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "upload":
            receipt_image = request.FILES.get("receipt_image")
            if receipt_image:
                LoanDocument.objects.create(
                    loan=loan,
                    document_type=LoanDocument.DOCUMENT_CLOSURE,
                    image=receipt_image,
                    other_name="Closure Receipt"
                )
                
        elif action == "delete":
            doc_id = request.POST.get("doc_id")
            doc = get_object_or_404(LoanDocument, id=doc_id, loan=loan)
            doc.delete()
            
        return redirect("gold_loan:loan_close_upload", loan_id=loan.id)

    receipts = loan.documents.filter(document_type=LoanDocument.DOCUMENT_CLOSURE)
    
    return render(request, "gold_loan/closure/loan_close_upload.html", {
        "loan": loan,
        "receipts": receipts
    })


def loan_close_confirm(request, loan_id):
    """
    Step 4: Final Closure
    """
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Verify receipts exist
    if not loan.documents.filter(document_type=LoanDocument.DOCUMENT_CLOSURE).exists():
        return redirect("gold_loan:loan_close_upload", loan_id=loan.id)
        
    if request.method == "POST":
        # Check intent from session
        next_action = request.session.get('loan_closure_next_action', 'close')

        loan.status = Loan.STATUS_CLOSED
        loan.closed_at = timezone.now()
        loan.save()
        
        # Clear session flag
        if 'loan_closure_verified_id' in request.session:
            del request.session['loan_closure_verified_id']
        
        if next_action == 'extend':
            # Auto-redirect to extension logic
            return redirect(f"{reverse('gold_loan:loan_extend_action', args=[loan.id])}?from_closure=true")
            
        return redirect("gold_loan:loan_view", loan_id=loan.id)
    
    return redirect("gold_loan:loan_close_upload", loan_id=loan.id)


def loan_extend_otp(request, loan_id):
    """
    Verify OTP before extending a loan.
    """
    loan = get_object_or_404(Loan, id=loan_id)
    
    if loan.status != Loan.STATUS_CLOSED:
        # Cannot extend active loan
        messages.error(request, "Only closed loans can be extended.")
        return redirect("gold_loan:loan_view", loan_id=loan.id)
    
    # Check if loan has already been extended
    if loan.extensions.exists():
        messages.error(request, "This loan has already been extended once. Multiple extensions are not allowed.")
        return redirect("gold_loan:loan_view", loan_id=loan.id)

    if request.method == "POST":
        otp = request.POST.get("otp")
        if otp == "123456": # Mock OTP
             return redirect("gold_loan:loan_extend_action", loan_id=loan.id)
        else:
             return render(request, "gold_loan/loan/loan_extend_otp.html", {
                "loan": loan,
                "error": "Invalid OTP. Please try again."
             })
             
    # GET: Send/Generate OTP
    return render(request, "gold_loan/loan/loan_extend_otp.html", {"loan": loan})


def loan_extend_action(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    from_closure = request.GET.get("from_closure") == "true"
    
    if not from_closure and loan.status != Loan.STATUS_CLOSED:
        # Cannot extend active loan unless coming from closure flow
        messages.error(request, "Only closed loans can be extended.")
        return redirect("gold_loan:loan_view", loan_id=loan.id)
    
    # Check if loan has already been extended
    if loan.extensions.exists():
        messages.error(request, "This loan has already been extended once. Multiple extensions are not allowed.")
        return redirect("gold_loan:loan_view", loan_id=loan.id)
        
    # Redirect to Step 1 with existing customer
    session = get_loan_session(request)
    session.clear() # Clear any staled session
    
    # Pre-select customer
    request.session["loan_entry"] = {
        "existing_customer_id": loan.customer.id,
        "parent_loan_id": loan.id
    }
    request.session.modified = True
    
    return redirect(f"/loan/entry/step-1/?customer_id={loan.customer.id}")
    





def loan_entry_step1(request):
    session = get_loan_session(request)

    if request.method == "POST":
        # Check if existing customer was selected
        existing_customer_id = request.POST.get("existing_customer_id", "").strip()
        
        if existing_customer_id:
            # Use existing customer
            try:
                customer = Customer.objects.get(id=existing_customer_id)
                session["existing_customer_id"] = existing_customer_id
                session["customer"] = None  # Clear any new customer data
                session["customer_photo"] = None
                request.session.modified = True
                return redirect("gold_loan:loan_entry_step2")
            except Customer.DoesNotExist:
                return render(request, "gold_loan/loan/step1_personal.html", {
                    "error": "Selected customer not found"
                })
        
        # NEW CUSTOMER - validate and save to session
        mobile_primary = request.POST.get("mobile_primary", "")
        aadhaar_number = request.POST.get("aadhaar_number", "")
        
        # Basic validation (model validators will also check)
        if len(mobile_primary) != 10 or not mobile_primary.isdigit():
            return render(request, "gold_loan/loan/step1_personal.html", {
                "error": "Mobile number must be exactly 10 digits"
            })
        
        if len(aadhaar_number) != 12 or not aadhaar_number.isdigit():
            return render(request, "gold_loan/loan/step1_personal.html", {
                "error": "Aadhaar number must be exactly 12 digits"
            })

        # NEW CUSTOMER
        customer_data = {
            "name": request.POST.get("name"),
            "mobile_primary": mobile_primary,
            "mobile_secondary": request.POST.get("mobile_secondary", ""),
            "email": request.POST.get("email", ""),
            "address": request.POST.get("address"),
            "aadhaar_number": aadhaar_number,
            "profession": request.POST.get("profession"),
            "nominee_name": request.POST.get("nominee_name"),
            "nominee_mobile": request.POST.get("nominee_mobile"),
        }

        # Save customer photo to temp location
        photo = request.FILES.get("customer_photo")
        photo_path = None
        
        if photo:
            # Ensure temp directory exists
            temp_loc = os.path.join(settings.MEDIA_ROOT, "temp_customers")
            if not os.path.exists(temp_loc):
                os.makedirs(temp_loc, exist_ok=True)
                
            fs = FileSystemStorage(location=temp_loc)
            filename = fs.save(photo.name, photo)
            photo_path = f"temp_customers/{filename}"

        session["customer"] = customer_data
        session["customer_photo"] = photo_path
        session["existing_customer_id"] = None  # Clear existing customer

        request.session.modified = True

        return redirect("gold_loan:loan_entry_step2")

    # Handle pre-selected customer for extension or other flows
    preselected_customer = None
    existing_id = request.GET.get("customer_id") or session.get("existing_customer_id")
    if existing_id:
        try:
            preselected_customer = Customer.objects.get(id=existing_id)
        except Customer.DoesNotExist:
            pass

    return render(request, "gold_loan/loan/step1_personal.html", {
        "preselected_customer": preselected_customer,
        "existing_data": session.get("customer"),
        "customer_photo": session.get("customer_photo")
    })



def loan_entry_step2(request):
    session = get_loan_session(request)

    if request.method == "POST":
        items = []

        names = request.POST.getlist("item_name[]")
        carats = request.POST.getlist("carat[]")
        gross_weights = request.POST.getlist("gross_weight[]")
        approved_weights = request.POST.getlist("approved_net_weight[]")
        item_counts = request.POST.getlist("item_count[]")
        descriptions = request.POST.getlist("description[]")

        # Ensure temp directory exists
        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_items")
        os.makedirs(temp_dir, exist_ok=True)
        fs = FileSystemStorage(location=temp_dir)

        existing_items = session.get("items", [])

        for index in range(len(names)):
            gross = Decimal(gross_weights[index])
            approved = Decimal(approved_weights[index])

            if approved > gross:
                # Build current items from POST data to preserve user input
                current_items = []
                for i in range(len(names)):
                    current_items.append({
                        "item_name": names[i],
                        "carat": int(carats[i]) if carats[i] else None,
                        "gross_weight": gross_weights[i],
                        "approved_net_weight": approved_weights[i],
                        "item_count": item_counts[i] if i < len(item_counts) else 1,
                        "description": descriptions[i],
                        "images": existing_items[i].get("images", []) if i < len(existing_items) else []
                    })
                return render(request, "gold_loan/loan/step2_items.html", {
                    "error": f"Item {index+1}: Approved Net Weight ({approved}g) cannot exceed Gross Weight ({gross}g).",
                    "items": current_items
                })
            
            if gross <= 0 or approved <= 0:
                # Build current items from POST data to preserve user input
                current_items = []
                for i in range(len(names)):
                    current_items.append({
                        "item_name": names[i],
                        "carat": int(carats[i]) if carats[i] else None,
                        "gross_weight": gross_weights[i],
                        "approved_net_weight": approved_weights[i],
                        "item_count": item_counts[i] if i < len(item_counts) else 1,
                        "description": descriptions[i],
                        "images": existing_items[i].get("images", []) if i < len(existing_items) else []
                    })
                return render(request, "gold_loan/loan/step2_items.html", {
                    "error": f"Item {index+1}: Weights must be positive values.",
                    "items": current_items
                })

            # Get images for this specific item
            new_images = request.FILES.getlist(f"item_images_{index}[]")
            
            # Check existing images for this card if available
            existing_image_paths = []
            if index < len(existing_items):
                existing_image_paths = existing_items[index].get("images", [])

            # Total images (new + existing)
            if len(new_images) + len(existing_image_paths) < 1:
                # Build current items from POST data to preserve user input
                current_items = []
                for i in range(len(names)):
                    current_items.append({
                        "item_name": names[i],
                        "carat": int(carats[i]) if carats[i] else None,
                        "gross_weight": gross_weights[i],
                        "approved_net_weight": approved_weights[i],
                        "item_count": item_counts[i] if i < len(item_counts) else 1,
                        "description": descriptions[i],
                        "images": existing_items[i].get("images", []) if i < len(existing_items) else []
                    })
                return render(request, "gold_loan/loan/step2_items.html", {
                    "error": f"Item {index+1}: Minimum 1 image is required.",
                    "items": current_items
                })

            image_paths = list(existing_image_paths) # Keep existing ones
            for img in new_images:
                filename = fs.save(img.name, img)
                image_paths.append(f"temp_items/{filename}")

            items.append({
                "item_name": names[index],
                "carat": int(carats[index]),  # Store as integer for template comparison
                "gross_weight": gross_weights[index],
                "approved_net_weight": approved_weights[index],
                "item_count": int(item_counts[index]) if index < len(item_counts) else 1,
                "description": descriptions[index],
                "images": image_paths,
            })

        session["items"] = items
        request.session.modified = True

        return redirect("gold_loan:loan_entry_step3")

    return render(request, "gold_loan/loan/step2_items.html", {
        "items": session.get("items", [])
    })




def loan_entry_step3(request):
    session = get_loan_session(request)

    if request.method == "POST":
        try:
            approved_grams = Decimal(request.POST.get("approved_grams"))
            price_per_gram = Decimal(request.POST.get("price_per_gram"))
            interest_rate = Decimal(request.POST.get("interest_rate", "0"))
        except (ValueError, TypeError, DecimalException):
            # Recalculate total_approved_grams for context if an error occurs here
            total_approved_grams_for_context = Decimal("0")
            items = session.get("items", [])
            for item in items:
                approved_weight = item.get("approved_net_weight", "0")
                try:
                    total_approved_grams_for_context += Decimal(approved_weight)
                except:
                    pass
            # Preserve user input from POST data
            loan_data = {
                "lot_number": request.POST.get("lot_number", ""),
                "interest_rate": request.POST.get("interest_rate", ""),
                "price_per_gram": request.POST.get("price_per_gram", ""),
            }
            return render(request, "gold_loan/loan/step3_loan.html", {
                "error": "Invalid numeric values provided.",
                "total_approved_grams": total_approved_grams_for_context,
                "loan_data": loan_data
            })

        if price_per_gram <= 0 or interest_rate < 0:
            # Recalculate total_approved_grams for context if an error occurs here
            total_approved_grams_for_context = Decimal("0")
            items = session.get("items", [])
            for item in items:
                approved_weight = item.get("approved_net_weight", "0")
                try:
                    total_approved_grams_for_context += Decimal(approved_weight)
                except:
                    pass
            # Preserve user input from POST data
            loan_data = {
                "lot_number": request.POST.get("lot_number", ""),
                "interest_rate": str(interest_rate),
                "price_per_gram": str(price_per_gram),
            }
            return render(request, "gold_loan/loan/step3_loan.html", {
                "error": "Price per gram must be positive and Interest rate cannot be negative.",
                "total_approved_grams": total_approved_grams_for_context,
                "loan_data": loan_data
            })

        # Validate Lot Occupancy
        lot_number = request.POST.get("lot_number", "").strip()
        occupied = Loan.objects.filter(lot_number=lot_number).exclude(status=Loan.STATUS_CLOSED).exists()
        
        if occupied:
            # Recalculate context for error
            total_approved_grams_for_context = Decimal("0")
            items = session.get("items", [])
            for item in items:
                try: total_approved_grams_for_context += Decimal(item.get("approved_net_weight", "0"))
                except: pass
            
            return render(request, "gold_loan/loan/step3_loan.html", {
                "error": f"Lot Number '{lot_number}' is already in use by another active loan record.",
                "total_approved_grams": total_approved_grams_for_context,
                "loan_data": request.POST
            })

        session["loan"] = {
            "lot_number": lot_number,
            "interest_rate": request.POST.get("interest_rate"),
            "price_per_gram": str(price_per_gram),
            "approved_grams": str(approved_grams),
            "total_amount": str(approved_grams * price_per_gram),
        }

        request.session.modified = True
        return redirect("gold_loan:loan_entry_step4")

    # Calculate total approved grams from items in step 2
    total_approved_grams = Decimal("0")
    items = session.get("items", [])
    
    for item in items:
        approved_weight = item.get("approved_net_weight", "0")
        try:
            total_approved_grams += Decimal(approved_weight)
        except:
            pass
    
    context = {
        "total_approved_grams": total_approved_grams,
        "loan_data": session.get("loan"),
        "loan_number": Loan.generate_loan_number()
    }

    return render(request, "gold_loan/loan/step3_loan.html", context)



def loan_entry_step4(request):
    session = get_loan_session(request)

    if request.method == "POST":
        docs = []

        types = request.POST.getlist("document_type[]")
        names = request.POST.getlist("other_document_name[]")
        images = request.FILES.getlist("document_image[]")

        # Ensure temp directory exists
        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_documents")
        os.makedirs(temp_dir, exist_ok=True)
        fs = FileSystemStorage(location=temp_dir)

        if not types:
            return render(request, "gold_loan/loan/step4_documents.html", {
                "error": "At least one document is required.",
                "documents": session.get("documents", [])
            })

        existing_docs = session.get("documents", [])

        for i in range(len(types)):
            # Get new image if uploaded
            try:
                doc_image = request.FILES.getlist("document_image[]")[i]
            except (IndexError, KeyError):
                doc_image = None
            
            # Check existing image for this row
            existing_image_path = None
            if i < len(existing_docs):
                existing_image_path = existing_docs[i].get("image")

            # Error if no image exists anywhere
            if not doc_image and not existing_image_path:
                # Build current documents from POST data to preserve user input
                current_docs = []
                for j in range(len(types)):
                    current_docs.append({
                        "document_type": types[j],
                        "other_name": names[j] if j < len(names) else "",
                        "image": existing_docs[j].get("image") if j < len(existing_docs) else None
                    })
                return render(request, "gold_loan/loan/step4_documents.html", {
                    "error": f"Document {i+1}: Image is required.",
                    "documents": current_docs
                })
            
            image_path = existing_image_path
            if doc_image:
                filename = fs.save(doc_image.name, doc_image)
                image_path = f"temp_documents/{filename}"

            docs.append({
                "document_type": types[i],
                "other_name": names[i] if i < len(names) else "",
                "image": image_path,
            })

        session["documents"] = docs
        request.session.modified = True

        return redirect("gold_loan:loan_entry_step5")

    return render(request, "gold_loan/loan/step4_documents.html", {
        "documents": session.get("documents", [])
    })




def loan_entry_step5(request):
    session = request.session.get("loan_entry")

    if not session:
        return redirect("gold_loan:loan_entry_step1")

    if request.method == "POST":
        otp = request.POST.get("otp")

        if otp != "123456":
            return render(request, "gold_loan/loan/step5_otp.html", {
                "error": "Invalid OTP"
            })

        try:
            with transaction.atomic():
                # -----------------------
                # CUSTOMER
                # -----------------------
                existing_customer_id = session.get("existing_customer_id")
                
                if existing_customer_id:
                    # Use existing customer
                    customer = Customer.objects.get(id=existing_customer_id)
                else:
                    # Create new customer
                    customer_data = session["customer"].copy()
                    
                    # Handle customer photo
                    customer_photo_path = session.get("customer_photo")
                    
                    # Create customer first without photo
                    customer = Customer.objects.create(**customer_data)
                    
                    if customer_photo_path:
                        # Construct full path to temp file
                        full_temp_path = os.path.join(settings.MEDIA_ROOT, customer_photo_path)
                        
                        if os.path.exists(full_temp_path):
                            with open(full_temp_path, 'rb') as f:
                                # Save to model field - this moves it to 'customers/photos/' as per model definition
                                customer.photo.save(os.path.basename(customer_photo_path), File(f), save=True)
                            
                            # Clean up temp file
                            try:
                                os.remove(full_temp_path)
                            except OSError:
                                pass


                # -----------------------
                # LOAN
                # -----------------------
                loan_data = session["loan"]
                
                # Initial Interest Logic
                now = timezone.now()
                # 10 Days interest upfront
                # Formula: (principal * rate * 10) / (365 * 100)
                principal = Decimal(loan_data["total_amount"])
                rate = Decimal(loan_data["interest_rate"])
                initial_interest = (principal * rate * 10) / (Decimal("365") * Decimal("100"))
                initial_interest = round(initial_interest, 2)

                loan_start = now
                interest_lock = now + timedelta(days=10)

                loan = Loan.objects.create(
                    customer=customer,
                    lot_number=loan_data["lot_number"], # Use chosen lot number
                    loan_number=Loan.generate_loan_number(),
                    interest_rate=loan_data["interest_rate"],
                    price_per_gram=loan_data["price_per_gram"],
                    approved_grams=loan_data["approved_grams"],
                    total_amount=loan_data["total_amount"],
                    status=Loan.STATUS_ACTIVE,
                    
                    # Interest Logic Fields
                    pending_interest=initial_interest,
                    loan_start_date=loan_start,
                    interest_lock_until=interest_lock,
                    last_interest_calculated_at=loan_start,
                    parent_loan_id=session.get("parent_loan_id")
                )

                # -----------------------
                # GOLD ITEMS + IMAGES
                # -----------------------
                for item_data in session["items"]:
                    # Extract images before creating item
                    image_paths = item_data.pop("images", [])

                    gold_item = GoldItem.objects.create(
                        loan=loan,
                        item_name=item_data["item_name"],
                        carat=item_data["carat"],
                        gross_weight=item_data["gross_weight"],
                        approved_net_weight=item_data["approved_net_weight"],
                        description=item_data["description"],
                    )

                    # Create GoldItemBundle for item count
                    GoldItemBundle.objects.create(
                        gold_item=gold_item,
                        item_count=item_data.get("item_count", 1)
                    )

                    # Create images for this item
                    for img_path in image_paths:
                        GoldItemImage.objects.create(
                            gold_item=gold_item,
                            image=img_path
                        )

                # -----------------------
                # DOCUMENTS
                # -----------------------
                for doc_data in session.get("documents", []):
                    LoanDocument.objects.create(
                        loan=loan,
                        document_type=doc_data["document_type"],
                        other_name=doc_data.get("other_name", ""),
                        image=doc_data.get("image", "")
                    )

            # Clear session after successful save
            del request.session["loan_entry"]
            return redirect("gold_loan:dashboard")

        except Exception as e:
            # Handle errors (e.g., duplicate mobile/Aadhaar)
            error_message = str(e)
            if "mobile_primary" in error_message:
                error_message = "Mobile number already exists"
            elif "aadhaar_number" in error_message:
                error_message = "Aadhaar number already exists"
            else:
                error_message = f"Error saving loan: {error_message}"
            
            return render(request, "gold_loan/loan/step5_otp.html", {
                "error": error_message
            })

    return render(request, "gold_loan/loan/step5_otp.html")

def resend_otp_api(request):
    """Mock API to resend OTP"""
    if request.method == "POST":
        # In a real app, you would regenerate and send the SMS here
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=400)


# API Endpoints for customer search

def search_customers(request):
    """Search customers by name, mobile, aadhaar, or customer ID"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 1:
        return JsonResponse({'customers': []})
    
    # Search in name, mobile, aadhaar, and customer_id
    filters = (
        Q(name__icontains=query) | 
        Q(mobile_primary__icontains=query) |
        Q(aadhaar_number__icontains=query) |
        Q(customer_id__icontains=query)
    )
    
    # If query is numeric, also try to match exact DB ID (legacy support)
    if query.isdigit():
        filters |= Q(id=query)

    customers = Customer.objects.filter(filters)[:10]  # Limit to 10 results
    
    results = []
    for c in customers:
        photo_url = c.photo.url if c.photo else None
        results.append({
            'id': c.id,
            'customer_id': c.customer_id, # Use actual customer_id (PGxxxx)
            'name': c.name,
            'mobile_primary': c.mobile_primary,
            'aadhaar_number': c.aadhaar_number,
            'photo_url': photo_url
        })
    
    return JsonResponse({'customers': results})


def check_lot_vacancy(request):
    """Check if a lot number is available for use"""
    lot_number = request.GET.get('lot_number', '').strip()
    if not lot_number:
        return JsonResponse({'vacant': True})
    
    # Lot is occupied if used by ANY loan that is NOT closed
    is_used = Loan.objects.filter(lot_number=lot_number).exclude(status=Loan.STATUS_CLOSED).exists()
    return JsonResponse({'vacant': not is_used})


def get_customer(request, customer_id):
    """Get full customer details by ID"""
    try:
        customer = get_object_or_404(Customer, id=customer_id)
        
        data = {
            'success': True,
            'customer': {
                'id': customer.id,
                'customer_id': str(customer.id),
                'name': customer.name,
                'mobile_primary': customer.mobile_primary,
                'mobile_secondary': customer.mobile_secondary or '',
                'email': customer.email or '',
                'address': customer.address,
                'aadhaar_number': customer.aadhaar_number,
                'profession': customer.profession,
                'nominee_name': customer.nominee_name,
                'nominee_mobile': customer.nominee_mobile,
                'photo_url': customer.photo.url if customer.photo else None,
            }
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def _calculate_outstanding_principal(loan):
    total_principal_paid = loan.payments.aggregate(total=Sum('principal_component'))['total'] or Decimal('0')
    return loan.total_amount - total_principal_paid


def _update_loan_interest(loan):
    """
    Updates the pending interest for the loan based on time elapsed.
    Includes YEARLY capitalization logic.
    """
    if loan.status != Loan.STATUS_ACTIVE:
        return

    if not loan.last_interest_calculated_at or not loan.interest_lock_until:
        return

    now = timezone.now()
    
    # We loop until we catch up to 'now'
    # This loop handles multiple years passing (unlikely but robust)
    while True:
        # 1. Determine next capitalization date
        # If we never capitalized, start checking from loan_start_date
        # Otherwise, check from last_capitalization_date
        base_date = loan.last_capitalization_date or loan.loan_start_date
        next_cap_date = base_date + timedelta(days=365)
        
        # 2. Determine current calculation start point
        # Usually from last calculation, but constrained by interest lock (grace period)
        start_calc_time = max(loan.last_interest_calculated_at, loan.interest_lock_until)
        
        # 3. Check if we reached or passed the capitalization date
        if now > next_cap_date and next_cap_date > start_calc_time:
            # ---> CAPITALIZATION EVENT OCCURRED <---
            
            # Calculate interest up to the capitalization moment
            delta = next_cap_date - start_calc_time
            days = delta.days
            if days > 0:
                outstanding_principal = _calculate_outstanding_principal(loan)
                interest = (outstanding_principal * loan.interest_rate * days) / (Decimal("365") * Decimal("100"))
                loan.pending_interest += round(interest, 2)
            
            # CAPITALIZE
            if loan.pending_interest > 0:
                loan.total_amount += loan.pending_interest
                loan.pending_interest = Decimal("0.00")
            
            # Update timestamps
            loan.last_capitalization_date = next_cap_date
            loan.last_interest_calculated_at = next_cap_date
            loan.save()
            
            # Loop continues to handle post-capitalization time...
            continue
            
        else:
            # ---> NORMAL DAILY INTEREST <---
            # No capitalization event in this interval (or we passed it)
            
            if now > start_calc_time:
                delta = now - start_calc_time
                days = delta.days
                
                if days > 0:
                    outstanding_principal = _calculate_outstanding_principal(loan)
                    interest = (outstanding_principal * loan.interest_rate * days) / (Decimal("365") * Decimal("100"))
                    loan.pending_interest += round(interest, 2)
                    
                    loan.last_interest_calculated_at = now
                    loan.save()
            
            # We are up to date
            break 


def loan_view(request, loan_id):
    """
    Read-only view for a specific loan.
    Fetches Loan, Customer, GoldItems (with images), and Documents.
    """
    loan = get_object_or_404(
        Loan.objects.select_related("customer").prefetch_related(
            "items__images", 
            "documents",
            "payments"
        ),
        id=loan_id
    )

    # Trigger Interest Calculation
    _update_loan_interest(loan)
    
    # Recalculate context after update
    outstanding_principal = _calculate_outstanding_principal(loan)
    total_principal_paid = loan.payments.aggregate(total=Sum('principal_component'))['total'] or Decimal('0')
    total_paid = loan.payments.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    # Calculate Next Capitalization Date
    base_date = loan.last_capitalization_date or loan.loan_start_date or loan.created_at
    if loan.status == Loan.STATUS_CLOSED:
        next_cap_date = None
    else:
        next_cap_date = base_date + timedelta(days=365)

    # Fetch Pledge info
    pledge = getattr(loan, 'pledge', None)
    adjustments = []
    total_adjustment_amount = Decimal("0")
    if pledge:
        adjustments = pledge.adjustments.all().order_by('date')
        total_adjustment_amount = sum(a.amount for a in adjustments)

    # Check if this loan has already been extended
    has_been_extended = loan.extensions.exists()
    
    context = {
        "loan": loan,
        "customer": loan.customer,
        "items": loan.items.all(),
        "documents": loan.documents.all(),
        "outstanding_principal": outstanding_principal,
        "total_principal_paid": total_principal_paid,
        "total_paid": total_paid,
        "payments": loan.payments.all().order_by("-created_at"),
        "next_cap_date": next_cap_date,
        "pledge": pledge,
        "adjustments": adjustments,
        "total_adjustment_amount": total_adjustment_amount,
        "has_been_extended": has_been_extended,
    }
    return render(request, "gold_loan/loan/loan_view.html", context)


def loan_edit(request, loan_id):
    """
    Edit loan details: bank/pledge info, interest rate, and price per gram.
    Manages LoanPledge (Internal Company Data).
    Only available for ACTIVE loans.
    """
    loan = get_object_or_404(
        Loan.objects.select_related("customer").prefetch_related("items", "pledge__adjustments"),
        id=loan_id
    )
    
    # Redirect if loan is closed
    if loan.status == Loan.STATUS_CLOSED:
        return redirect("gold_loan:loan_view", loan_id=loan.id)
    
    # Get or create pledge
    pledge, created = LoanPledge.objects.get_or_create(loan=loan)
    
    error = None
    success = None
    
    if request.method == "POST":
        action = request.POST.get("action", "update_loan")

        try:
            if action == "update_loan":
                # Loan Configuration (Customer-facing/Accounting)
                # Only update if fields are present in POST (they might be commented out in UI)
                new_interest_rate = request.POST.get("interest_rate")
                new_price_per_gram = request.POST.get("price_per_gram")
                
                if new_interest_rate is not None and new_price_per_gram is not None:
                    try:
                        interest_rate = Decimal(new_interest_rate)
                        price_per_gram = Decimal(new_price_per_gram)
                        
                        if interest_rate < 0:
                            error = "Interest rate cannot be negative"
                        elif price_per_gram <= 0:
                            error = "Price per gram must be positive"
                        else:
                            loan.interest_rate = interest_rate
                            loan.price_per_gram = price_per_gram
                            loan.total_amount = loan.approved_grams * price_per_gram
                            loan.save()
                    except (InvalidOperation, DecimalException):
                        error = "Invalid numeric values for loan configuration"
                
                if not error:
                    # Update LoanPledge (Internal)
                    bank_name = request.POST.get("bank_name", "").strip()
                    bank_address = request.POST.get("bank_address", "").strip()
                    pledge_receipt_no = request.POST.get("pledge_receipt_no", "").strip()
                    
                    if not bank_name or not bank_address or not pledge_receipt_no:
                        error = "Bank Name, Address, and Pledge Receipt No are required for the pledge."
                    else:
                        with transaction.atomic():
                            # Save any loan changes if any happened above (already saved but transaction.atomic is good)
                            loan.save()
                            
                            # Update LoanPledge (Internal)
                            pledge.bank_name = bank_name
                            pledge.bank_address = bank_address
                            pledge.pledge_receipt_no = pledge_receipt_no
                            pledge.notes = request.POST.get("pledge_notes", "").strip()
                            
                            def get_decimal(val):
                                if not val or val.strip() == "":
                                    return Decimal("0")
                                return Decimal(val)

                            pledge.total_actual_grams = get_decimal(request.POST.get("total_actual_grams"))
                            pledge.total_approved_grams = get_decimal(request.POST.get("total_approved_grams"))
                            pledge.price_per_gram = get_decimal(request.POST.get("pledge_price_per_gram"))
                            pledge.interest_rate = get_decimal(request.POST.get("pledge_interest_rate"))
                            pledge.interest_period = request.POST.get("interest_period", "").strip()
                            
                            pledge.save()

                        # Handle Dynamic Rows for Adjustments
                        # We'll clear and recreate or update. For simplicity with dynamic rows, 
                        # usually we check for IDs or clear and recreate if small.
                        # But professional design: let's match the rows.
                        
                        # Get data from lists
                        adj_dates = request.POST.getlist("adj_date[]")
                        adj_amounts = request.POST.getlist("adj_amount[]")
                        adj_mediums = request.POST.getlist("adj_medium[]")
                        adj_notes = request.POST.getlist("adj_notes[]")
                        
                        # Clear existing adjustments and recreate
                        pledge.adjustments.all().delete()
                        for i in range(len(adj_amounts)):
                            if adj_amounts[i] and Decimal(adj_amounts[i]) != 0:
                                LoanPledgeAdjustment.objects.create(
                                    pledge=pledge,
                                    date=adj_dates[i] if adj_dates[i] else timezone.now().date(),
                                    amount=Decimal(adj_amounts[i]),
                                    medium=adj_mediums[i],
                                    notes=adj_notes[i]
                                )
                        
                        success = "Loan and Pledge details updated successfully"

                        # Update Gold Item Counts
                        item_ids = request.POST.getlist("item_id[]")
                        item_counts = request.POST.getlist("item_count[]")
                        for i in range(len(item_ids)):
                            if i < len(item_counts):
                                GoldItemBundle.objects.update_or_create(
                                    gold_item_id=item_ids[i],
                                    defaults={
                                        'item_count': int(item_counts[i])
                                    }
                                )

        except (ValueError, DecimalException) as e:
            error = f"Invalid numeric values provided: {str(e)}"
        except Exception as e:
            error = f"Error: {str(e)}"
    
    # Calculate totals for display
    total_actual_grams = loan.items.aggregate(total=Sum('gross_weight'))['total'] or Decimal('0')
    total_approved_grams = loan.approved_grams
    
    adjustments = pledge.adjustments.all().order_by('date')
    total_adjustment_amount = sum(a.amount for a in adjustments)
    
    context = {
        "loan": loan,
        "customer": loan.customer,
        "items": loan.items.all(),
        "pledge": pledge,
        "adjustments": adjustments,
        "total_actual_grams": total_actual_grams,
        "total_approved_grams": total_approved_grams,
        "total_adjustment_amount": total_adjustment_amount,
        "error": error,
        "success": success
    }
    return render(request, "gold_loan/loan/loan_edit.html", context)


def simulate_interest(request, loan_id):
    """
    API endpoint to simulate interest calculation for a specific number of days.
    Includes YEARLY capitalization impact.
    Does NOT update any database records.
    """
    loan = get_object_or_404(Loan, id=loan_id)
    
    try:
        # User explicitly providing 'days from NOW' logic would be simpler, 
        # but prompt says "Simulation inputs: simulate_days (from UI)" and "simulation_date = NOW + simulate_days"
        # However, UI field says "Days from Creation".
        # Let's clarify: The user prompt says "Simulate days from Creation" in UI label, 
        # but the logic description says "simulation_date = NOW + simulate_days".
        # If I type "400" in UI (which implies 400 days total tenure), but loan is 10 days old, 
        # do I add 400 days to NOW (total 410 days tenure)? Or do I aim for T+400?
        # Re-reading prompt: "Simulation is NOT a shortcut calculator... It must behave like a time machine... +8 days, +30 days".
        # Usually "+30 days" means "30 days from now".
        # BUT the UI label in previous steps was "Simulate Days from Creation".
        # To strictly follow the "AUTHORITATIVE SIMULATION RULES" provided in this step:
        # "simulation_date = NOW + simulate_days".
        # "From UI: simulate_days".
        # So I will interpret the input as "Add X days to today".
        # This is safer and more useful for "Future Projection".
        
        simulate_days = int(request.GET.get('days', 0))
    except ValueError:
        return JsonResponse({"error": "Invalid days provided"}, status=400)

    if simulate_days < 0:
        return JsonResponse({"error": "Days cannot be negative"}, status=400)

    # STEP 1: Establish Simulation Timeline
    now = timezone.now()
    simulation_date = now + timedelta(days=simulate_days)
    
    # STEP 2: Compute Current Outstanding Principal (Real history)
    # outstanding_principal = total_loan_amount - sum(principal_component)
    # We use the internal helper but need to respect current DB state
    total_principal_paid = loan.payments.aggregate(total=Sum('principal_component'))['total'] or Decimal('0')
    
    # We use local variables to simulate strict state
    sim_total_amount = loan.total_amount
    sim_outstanding_principal = sim_total_amount - total_principal_paid
    sim_pending_interest = loan.pending_interest
    
    # Track capitalizations
    capitalizations_applied = 0
    
    # We need to simulate strictly from "Current State" moving forward to "Simulation Date"
    # Current Pointer: Start from logic's last update or NOW?
    # Logic says "Use system date (NOW) as base".
    # So we simulate interval [NOW, simulation_date].
    
    current_pointer = now
    
    # Last capitalization date (from DB)
    last_cap_date = loan.last_capitalization_date or loan.loan_start_date or loan.created_at
    
    # If loan hasn't started yet (e.g. grace period logic might use loan_start_date), handle that.
    # Assuming loan_start_date is set on creation.
    
    # LOOP: We iterate day-by-day or event-by-event?
    # Event-based is faster. Events: Yearly Boundaries.
    
    while current_pointer < simulation_date:
        
        # Determine next event: Next Yearly Capitalization
        # Logic: loan_start_date + (365 * N)
        # We need to find the *next* boundary after current_pointer
        
        # Calculate years elapsed since start to find potential next cap
        # (current_pointer - start) // 365 ?
        # Robust: Keep adding 365 to last_cap_date until > current_pointer?
        # But we must respect the "Next Capitalization Date" based on loan_start_date, not shifted by irregularities.
        # Actually in _update_loan_interest we did: `next_cap_date = base_date + 365` where base was last_cap.
        # This implies floating capitalization dates based on when the last one processed? 
        # The prompt says: "loan_start_date + (365 * N days)". Fixed schedule.
        # So let's stick to Fixed Schedule from loan_start_date.
        
        if not loan.loan_start_date:
            # Should not happen for active loan
            break
            
        # Determine N for next boundary
        # Time since start
        time_since_start = current_pointer - loan.loan_start_date
        days_since_start = time_since_start.days
        current_year_index = (days_since_start // 365) + 1 # Next boundary is end of this year
        
        next_cap_boundary = loan.loan_start_date + timedelta(days=365 * current_year_index)
        
        # If we already passed this boundary effectively (e.g. last_cap_date is >= next_cap_boundary), skip to next
        # (Handle case where DB is ahead or behind, but we simulate from NOW)
        if last_cap_date and last_cap_date >= next_cap_boundary:
             current_year_index += 1
             next_cap_boundary = loan.loan_start_date + timedelta(days=365 * current_year_index)
        
        # Determine segment end
        segment_end = min(simulation_date, next_cap_boundary)
        
        # STEP 3: Apply Grace Period Rule check
        # If segment is within grace period, no interest.
        # interest_lock_until might vary.
        
        # We process the interval [current_pointer, segment_end]
        
        # Start of calculating daily interest
        days_to_calc = (segment_end - current_pointer).days
        
        # BUT: Ensure we are past grace period
        # Effective start for interest in this segment
        interest_start_time = max(current_pointer, loan.interest_lock_until)
        
        if segment_end > interest_start_time:
            # We have valid interest days
            # Recalculate days based on effective start
            valid_days = (segment_end - interest_start_time).days
            
            # Additional check: If segment_end was purely inside grace, valid_days <= 0
            if valid_days > 0:
                # Step 5: Apply Daily Interest
                # Interest on *Current* Outstanding Principal
                # sim_outstanding_principal is valid here
                
                interest = (sim_outstanding_principal * loan.interest_rate * valid_days) / (Decimal("365") * Decimal("100"))
                sim_pending_interest += interest
        
        # Advance pointer
        current_pointer = segment_end
        
        # STEP 4: Apply Yearly Capitalization (If we hit boundary)
        if current_pointer == next_cap_boundary:
            # Check conditions
            # 1. Loan Active (Simulated always active unless we add closure logic, but prompt says Ignore Closed Loans - we assume strict simulation on active)
            # 2. Pending Interest > 0
            # 3. Boundary > last_capitalization_at (Managed by our loop progression + DB check check)
            
            if sim_pending_interest > 0:
                # Capitalize
                sim_total_amount += sim_pending_interest
                # Update Principal too!
                # Outstanding Principal = Total Amount - Paid
                # Since Paid is constant, Outstanding increases by same amount
                sim_outstanding_principal += sim_pending_interest
                
                sim_pending_interest = Decimal("0.00")
                capitalizations_applied += 1
                
                # Mark applied (update last_cap_date for loop logic if needed, but we rely on N * 365)
                last_cap_date = current_pointer

    # STEP 6: Final Output
    sim_total_payable = sim_outstanding_principal + sim_pending_interest
    
    return JsonResponse({
        "days": simulate_days, # Days added
        "simulated_date": simulation_date.strftime("%d %b %Y"),
        "current_principal": float(sim_outstanding_principal),
        "simulated_interest": float(sim_pending_interest),
        "total_payable": float(sim_total_payable),
        "capitalizations_count": capitalizations_applied,
        "interest_rate": float(loan.interest_rate)
    })


def loan_payment_view(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    
    # 1. Update Interest
    _update_loan_interest(loan)
    
    # 2. Calculate dynamic values
    outstanding_principal = _calculate_outstanding_principal(loan)
    total_principal_paid = loan.payments.aggregate(total=Sum('principal_component'))['total'] or Decimal('0')
    total_paid = loan.payments.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    error = None
    success = None

    if request.method == "POST":
        try:
            amount = Decimal(request.POST.get("amount"))
            mode = request.POST.get("payment_mode")
            reference = request.POST.get("reference_no", "")
            remarks = request.POST.get("remarks", "")
            date_str = request.POST.get("payment_date") # If we want backdated payments? 
            # Prompt says: "Payment Date (default = today)". 
            # Doesn't explicitly say we can change it, but UI requirement says "Add Payment Form -> Payment Date (default = today)"
            # If we allow changing date, interest calc gets complex.
            # "Bring Interest Up-to-Date" step implies strict timeline.
            # If user selects past date, we shouldn't have seemingly magically updated interest to NOW.
            # BUT the "Interest First Rule" relies on accurate 'pending_interest'.
            # Let's assume for now payment is effectively "today" or we treat the effective date as now for calculation.
            # OR we just use `payment_date` for record keeping and `now` for calculation.
            # Given the strict "Bring Interest Up-to-Date" rule logic: "If now >= interest_lock_until... add to pending".
            # This implies the logic is bound to 'now'.
            
            # Validation
            if loan.status != Loan.STATUS_ACTIVE:
                raise ValueError("Cannot add payment to closed loan.")
                
            if amount <= 0:
                raise ValueError("Payment amount must be greater than 0.")
            
            total_due = loan.pending_interest + outstanding_principal
            # Allow paying more? "Payment amount <= (pending_interest + outstanding_principal)"
            if amount > total_due:
                # Floating point issues might make it slightly off, handle carefully?
                # Decimal comparison should be precise.
                raise ValueError(f"Amount cannot exceed total due (₹{total_due})")

            with transaction.atomic():
                # Step A: Interest already brought up-to-date by _update_loan_interest(loan) at start of view.
                
                # Step B: Split Payment
                interest_component = min(loan.pending_interest, amount)
                remaining_after_interest = amount - interest_component
                
                principal_component = min(outstanding_principal, remaining_after_interest)
                
                # Step C: Update Balances
                loan.pending_interest -= interest_component
                loan.save()
                
                # Create Payment Record
                Payment.objects.create(
                    loan=loan,
                    total_amount=amount,
                    interest_component=interest_component,
                    principal_component=principal_component,
                    payment_mode=mode,
                    reference_no=reference,
                    remarks=remarks,
                    payment_date=date_str if date_str else timezone.now().date()
                )
                
                # Recalculate outstanding after payment to check for closure?
                # Does prompt ask for auto-closure?
                # "Loan must be ACTIVE" -> "Closed loans cannot accept payments".
                # "Loan closure accuracy" -> implied we might close it manually or it reaches 0.
                # If principal becomes 0 and pending_interest is 0, is it closed?
                # The user says "Loan can be closed safely" in expected result.
                # Maybe strictly manual closure?
                # Let's just redirect to payment page with success.
                return redirect("gold_loan:loan_payment_view", loan_id=loan.id)

        except ValueError as e:
            error = str(e)
        except Exception as e:
            error = f"An unexpected error occurred: {str(e)}"

    context = {
        "loan": loan,
        "outstanding_principal": outstanding_principal,
        "total_principal_paid": total_principal_paid,
        "total_paid": total_paid,
        "total_due": outstanding_principal + loan.pending_interest,
        "payments": loan.payments.all().order_by("-created_at"),
        "error": error,
        "today_date": timezone.now().strftime("%Y-%m-%d")
    }
    return render(request, "gold_loan/payment/payment.html", context)


# =========================
# RECEIPTS
# =========================

def loan_receipt(request, loan_id):
    loan = get_object_or_404(
        Loan.objects.select_related("customer").prefetch_related("items__images", "items__bundle", "documents"),
        id=loan_id
    )
    
    # Calculate item totals
    total_items = loan.items.count()
    total_weight = loan.items.aggregate(total=Sum('approved_net_weight'))['total'] or 0
    total_pieces = sum(item.bundle.item_count for item in loan.items.all() if hasattr(item, 'bundle'))

    context = {
        "loan": loan,
        "customer": loan.customer,
        "items": loan.items.all(),
        "total_items": total_items,
        "total_pieces": total_pieces,
        "total_weight": total_weight,
        "now": timezone.now()
    }
    return render(request, "gold_loan/loan/loan_receipt.html", context)


def payment_summary_receipt(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Ensure interest is up to date for display
    _update_loan_interest(loan)
    
    outstanding_principal = _calculate_outstanding_principal(loan)
    
    payments = loan.payments.all().order_by("payment_date", "created_at")
    
    # Aggregates
    total_loan_amount = loan.total_amount
    total_interest_paid = payments.aggregate(sum=Sum('interest_component'))['sum'] or Decimal('0')
    total_principal_paid = payments.aggregate(sum=Sum('principal_component'))['sum'] or Decimal('0')
    total_amount_paid = payments.aggregate(sum=Sum('total_amount'))['sum'] or Decimal('0')
    
    context = {
        "loan": loan,
        "customer": loan.customer,
        "payments": payments,
        "outstanding_principal": outstanding_principal,
        "total_loan_amount": total_loan_amount,
        "total_interest_paid": total_interest_paid,
        "total_principal_paid": total_principal_paid,
        "total_amount_paid": total_amount_paid,
        "now": timezone.now()
    }
    return render(request, "gold_loan/payment/payment_summary_receipt.html", context)


def payment_receipt(request, payment_id):
    payment = get_object_or_404(Payment.objects.select_related("loan", "loan__customer"), id=payment_id)
    
    context = {
        "payment": payment,
        "loan": payment.loan,
        "customer": payment.loan.customer,
        "now": timezone.now()
    }
    return render(request, "gold_loan/payment/payment_receipt.html", context)


def loan_closure_receipt(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    
    if loan.status != Loan.STATUS_CLOSED:
        # Should not exist for open loans
        pass # Or handle error
        
    # Calculation for totals for receipt
    payments = loan.payments.all()
    total_paid_amount = payments.aggregate(sum=Sum('total_amount'))['sum'] or Decimal('0')
    
    context = {
        "loan": loan,
        "customer": loan.customer,
        "total_paid_amount": total_paid_amount,
        "now": timezone.now()
    }
    return render(request, "gold_loan/closure/loan_closure_receipt.html", context)


# =========================
# CUSTOMER VIEWS
# =========================

def customer_list(request):
    """
    List all customers with basic details and loan counts.
    Supports searching by name, ID, or mobile.
    """
    query = request.GET.get('q', '').strip()
    customers = Customer.objects.annotate(
        total_loans=Count('loans')
    )

    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(customer_id__icontains=query) |
            Q(mobile_primary__icontains=query)
        )

    customers = customers.order_by('-id')
    
    context = {
        "customers": customers,
        "search_query": query
    }
    return render(request, "gold_loan/customer/customer_list.html", context)


def customer_detail(request, customer_id):
    """
    Show details for a specific customer and their loans.
    """
    customer = get_object_or_404(Customer, id=customer_id)
    
    # Fetch all loans for this customer
    loans_qs = Loan.objects.filter(customer=customer).order_by('-created_at')
    
    # Annotate paid principal
    loans_qs = loans_qs.annotate(
        paid_principal=Sum('payments__principal_component')
    )
    
    # Check Active/Closed counts
    total_active = loans_qs.filter(status=Loan.STATUS_ACTIVE).count()
    total_closed = loans_qs.filter(status=Loan.STATUS_CLOSED).count()

    # Process loans to attach calculated field
    loans_list = []
    for loan in loans_qs:
        paid = loan.paid_principal or Decimal('0')
        loan.calculated_outstanding_principal = loan.total_amount - paid
        loans_list.append(loan)
    
    context = {
        "customer": customer,
        "loans": loans_list,
        "total_active_loans": total_active,
        "total_closed_loans": total_closed,
    }
    return render(request, "gold_loan/customer/customer_detail.html", context)



def customer_create(request):
    """
    Create a new customer independently (not part of loan entry flow).
    """
    error = None
    
    if request.method == "POST":
        try:
            # Get form data
            name = request.POST.get("name")
            mobile_primary = request.POST.get("mobile_primary")
            mobile_secondary = request.POST.get("mobile_secondary", "")
            email = request.POST.get("email", "")
            address = request.POST.get("address")
            aadhaar_number = request.POST.get("aadhaar_number")
            profession = request.POST.get("profession")
            nominee_name = request.POST.get("nominee_name")
            nominee_mobile = request.POST.get("nominee_mobile")
            photo = request.FILES.get("photo")
            
            # Validation
            if not all([name, mobile_primary, address, aadhaar_number, profession, nominee_name, nominee_mobile]):
                raise ValueError("All mandatory fields (*) must be filled.")
            
            if len(mobile_primary) != 10 or not mobile_primary.isdigit():
                raise ValueError("Mobile number must be exactly 10 digits.")
            
            if len(aadhaar_number) != 12 or not aadhaar_number.isdigit():
                raise ValueError("Aadhaar number must be exactly 12 digits.")
            
            if mobile_secondary and (len(mobile_secondary) != 10 or not mobile_secondary.isdigit()):
                raise ValueError("Secondary mobile number must be exactly 10 digits.")
            
            if nominee_mobile and (len(nominee_mobile) != 10 or not nominee_mobile.isdigit()):
                raise ValueError("Nominee mobile number must be exactly 10 digits.")
            
            # Create customer
            customer = Customer.objects.create(
                name=name,
                mobile_primary=mobile_primary,
                mobile_secondary=mobile_secondary,
                email=email,
                address=address,
                aadhaar_number=aadhaar_number,
                profession=profession,
                nominee_name=nominee_name,
                nominee_mobile=nominee_mobile
            )
            
            if photo:
                customer.photo = photo
                customer.save()
            
            messages.success(request, f"Customer '{customer.name}' created successfully!")
            return redirect("gold_loan:customer_detail", customer_id=customer.id)
            
        except Exception as e:
            error = str(e)
            # Re-populate form with submitted data on error
            return render(request, "gold_loan/customer/customer_create.html", {
                "error": error,
                "form_data": request.POST
            })
    
    return render(request, "gold_loan/customer/customer_create.html", {
        "error": error
    })


def customer_edit(request, customer_id):

    """
    Edit existing customer details.
    """
    customer = get_object_or_404(Customer, id=customer_id)
    error = None

    if request.method == "POST":
        # Capture data so we can re-populate on error if needed
        # But for simple fields without complex validation other than required, 
        # let's just use the object.
        try:
            name = request.POST.get("name")
            mobile_secondary = request.POST.get("mobile_secondary", "")
            email = request.POST.get("email", "")
            address = request.POST.get("address")
            profession = request.POST.get("profession")
            nominee_name = request.POST.get("nominee_name")
            nominee_mobile = request.POST.get("nominee_mobile")

            # Update fields
            customer.name = name
            customer.mobile_secondary = mobile_secondary
            customer.email = email
            customer.address = address
            customer.profession = profession
            customer.nominee_name = nominee_name
            customer.nominee_mobile = nominee_mobile

            # Validation (simple manual check for required fields)
            if not all([name, address, profession, nominee_name, nominee_mobile]):
                raise ValueError("All mandatory fields (*) must be filled.")

            # Handle photo upload
            if "photo" in request.FILES:
                photo = request.FILES["photo"]
                customer.photo = photo

            customer.save()
            messages.success(request, "Customer details updated successfully.")
            return redirect("gold_loan:customer_detail", customer_id=customer.id)

        except Exception as e:
            error = str(e)

    return render(request, "gold_loan/customer/customer_edit.html", {
        "customer": customer,
        "error": error
    })


def analytics_dashboard(request):
    """
    Admin Analytics & Reports Dashboard
    Provides comprehensive system overview with key metrics and trends
    """
    # Basic Counts
    total_customers = Customer.objects.count()
    total_loans = Loan.objects.count()
    active_loans_count = Loan.objects.filter(status=Loan.STATUS_ACTIVE).count()
    closed_loans_count = Loan.objects.filter(status=Loan.STATUS_CLOSED).count()
    extended_loans_count = Loan.objects.filter(parent_loan__isnull=False).count()
    
    # Financial Metrics
    total_disbursed = Loan.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_recovered = Payment.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Active Loans Financial Data
    active_loans = Loan.objects.filter(status=Loan.STATUS_ACTIVE)
    total_active_principal = Decimal('0')
    total_pending_interest = Decimal('0')
    
    for loan in active_loans:
        _update_loan_interest(loan)
        outstanding = _calculate_outstanding_principal(loan)
        total_active_principal += outstanding
        total_pending_interest += loan.pending_interest
    
    # Loans by Status (for pie chart)
    loans_by_status = {
        'active': active_loans_count,
        'closed': closed_loans_count,
        'extended': extended_loans_count
    }
    
    # Daily Loan Creation Trend (Last 30 days)
    from datetime import date
    today = date.today()
    daily_trends = []
    
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        count = Loan.objects.filter(created_at__date=day).count()
        daily_trends.append({
            'date': day.strftime('%b %d'),
            'count': count
        })
    
    # Monthly Loan Creation (Last 12 months)
    monthly_trends = []
    for i in range(11, -1, -1):
        month_start = today.replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        count = Loan.objects.filter(created_at__date__gte=month_start, created_at__date__lte=month_end).count()
        monthly_trends.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })
    
    # Top Customers by Loan Count
    from django.db.models import Count as CountAgg
    top_customers = Customer.objects.annotate(
        loan_count=CountAgg('loans')
    ).filter(loan_count__gt=0).order_by('-loan_count')[:5]
    
    # Recent Activity (Last 10 loans)
    recent_loans = Loan.objects.select_related('customer').order_by('-created_at')[:10]
    
    # Overdue/Pending Analysis
    overdue_loans = []
    for loan in active_loans:
        if loan.pending_interest > 0:
            overdue_loans.append(loan)
    
    context = {
        'total_customers': total_customers,
        'total_loans': total_loans,
        'active_loans_count': active_loans_count,
        'closed_loans_count': closed_loans_count,
        'extended_loans_count': extended_loans_count,
        'total_disbursed': total_disbursed,
        'total_recovered': total_recovered,
        'total_active_principal': total_active_principal,
        'total_pending_interest': total_pending_interest,
        'loans_by_status': loans_by_status,
        'daily_trends': daily_trends,
        'monthly_trends': monthly_trends,
        'top_customers': top_customers,
        'recent_loans': recent_loans,
        'overdue_count': len(overdue_loans),
        # Chart Data prepared for JSON output
        'status_chart_data': {
            'labels': ['Active', 'Closed', 'Extended'],
            'data': [
                loans_by_status.get('active', 0),
                loans_by_status.get('closed', 0),
                loans_by_status.get('extended', 0)
            ]
        },
        'daily_chart_data': {
            'labels': [item['date'] for item in daily_trends],
            'data': [item['count'] for item in daily_trends]
        },
        'monthly_chart_data': {
            'labels': [item['month'] for item in monthly_trends],
            'data': [item['count'] for item in monthly_trends]
        }
    }
    
    return render(request, "gold_loan/analytics/analytics_dashboard.html", context)


def export_report(request):
    """
    Export reports in PDF or Excel format with optional date filtering.
    Supports: all_loans, active_loans, closed_loans, extended_loans, customers
    """
    from django.http import HttpResponse
    from datetime import datetime
    
    report_type = request.GET.get('report_type', 'all_loans')
    export_format = request.GET.get('format', 'pdf')
    date_cutoff = request.GET.get('date_cutoff', '')
    
    # Parse date cutoff
    cutoff_date = None
    if date_cutoff:
        try:
            cutoff_date = datetime.strptime(date_cutoff, '%Y-%m-%d')
        except ValueError:
            pass
    
    # Prepare data based on report type
    if report_type == 'all_loans':
        queryset = Loan.objects.select_related('customer').all()
        if cutoff_date:
            queryset = queryset.filter(created_at__lte=cutoff_date)
        data = _prepare_loan_data(queryset)
        title = "All Loans Report"
        
    elif report_type == 'active_loans':
        queryset = Loan.objects.select_related('customer').filter(status=Loan.STATUS_ACTIVE)
        if cutoff_date:
            queryset = queryset.filter(created_at__lte=cutoff_date)
        data = _prepare_loan_data(queryset)
        title = "Active Loans Report"
        
    elif report_type == 'closed_loans':
        queryset = Loan.objects.select_related('customer').filter(status=Loan.STATUS_CLOSED)
        if cutoff_date:
            queryset = queryset.filter(created_at__lte=cutoff_date)
        data = _prepare_loan_data(queryset)
        title = "Closed Loans Report"
        
    elif report_type == 'extended_loans':
        queryset = Loan.objects.select_related('customer', 'parent_loan').filter(parent_loan__isnull=False)
        if cutoff_date:
            queryset = queryset.filter(created_at__lte=cutoff_date)
        data = _prepare_extended_loan_data(queryset)
        title = "Extended Loans Report"
        
    elif report_type == 'customers':
        queryset = Customer.objects.all()
        if cutoff_date:
            # For customers, we filter by the first loan's creation date
            queryset = queryset.filter(loans__created_at__lte=cutoff_date).distinct()
        data = _prepare_customer_data(queryset)
        title = "Customer Details Report"
    else:
        return HttpResponse("Invalid report type", status=400)
    
    # Generate report
    if export_format == 'pdf':
        return _generate_pdf_report(data, title, date_cutoff)
    elif export_format == 'excel':
        return _generate_excel_report(data, title, date_cutoff)
    else:
        return HttpResponse("Invalid format", status=400)


def _prepare_loan_data(queryset):
    """Prepare loan data for export"""
    data = []
    headers = ['Loan Number', 'Customer Name', 'Customer ID', 'Mobile', 'Lot Number', 
               'Total Amount (₹)', 'Interest Rate (%)', 'Status', 'Created Date']
    
    for loan in queryset:
        data.append([
            loan.loan_number,
            loan.customer.name,
            loan.customer.customer_id or 'N/A',
            loan.customer.mobile_primary,
            loan.lot_number,
            f"{loan.total_amount:.2f}",
            f"{loan.interest_rate:.2f}",
            loan.get_status_display(),
            loan.created_at.strftime('%d-%b-%Y'),
        ])
    
    return {'headers': headers, 'rows': data}


def _prepare_extended_loan_data(queryset):
    """Prepare extended loan data for export"""
    data = []
    headers = ['Loan Number', 'Customer Name', 'Parent Loan', 'Total Amount (₹)', 
               'Interest Rate (%)', 'Status', 'Created Date']
    
    for loan in queryset:
        data.append([
            loan.loan_number,
            loan.customer.name,
            loan.parent_loan.loan_number if loan.parent_loan else 'N/A',
            f"{loan.total_amount:.2f}",
            f"{loan.interest_rate:.2f}",
            loan.get_status_display(),
            loan.created_at.strftime('%d-%b-%Y'),
        ])
    
    return {'headers': headers, 'rows': data}


def _prepare_customer_data(queryset):
    """Prepare customer data for export"""
    data = []
    headers = ['Customer ID', 'Name', 'Mobile Primary', 'Mobile Secondary', 
               'Email', 'Address', 'Profession', 'Aadhaar', 'Nominee Name', 'Nominee Mobile']
    
    for customer in queryset:
        data.append([
            customer.customer_id or 'N/A',
            customer.name,
            customer.mobile_primary,
            customer.mobile_secondary or 'N/A',
            customer.email or 'N/A',
            customer.address,
            customer.profession,
            customer.aadhaar_number,
            customer.nominee_name,
            customer.nominee_mobile,
        ])
    
    return {'headers': headers, 'rows': data}


def _generate_excel_report(data, title, date_cutoff):
    """Generate Excel report using CSV format (compatible without external libraries)"""
    from django.http import HttpResponse
    from datetime import datetime
    
    response = HttpResponse(content_type='text/csv')
    filename = f"{title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # Write metadata
    writer.writerow([title])
    writer.writerow([f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}"])
    if date_cutoff:
        writer.writerow([f"Data up to: {date_cutoff}"])
    writer.writerow([])  # Empty row
    
    # Write headers
    writer.writerow(data['headers'])
    
    # Write data rows
    for row in data['rows']:
        writer.writerow(row)
    
    return response


def _generate_pdf_report(data, title, date_cutoff):
    """Generate PDF report using HTML template and simple rendering"""
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from datetime import datetime
    
    # Try to use xhtml2pdf if available, otherwise fall back to HTML
    try:
        from xhtml2pdf import pisa
        from io import BytesIO
        
        context = {
            'title': title,
            'generated_date': datetime.now().strftime('%d %B %Y, %I:%M %p'),
            'date_cutoff': date_cutoff,
            'headers': data['headers'],
            'rows': data['rows'],
        }
        
        html = render_to_string('gold_loan/reports/pdf_template.html', context)
        
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"{title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            return HttpResponse("Error generating PDF", status=500)
            
    except ImportError:
        # Fallback: Return HTML that can be printed as PDF
        context = {
            'title': title,
            'generated_date': datetime.now().strftime('%d %B %Y, %I:%M %p'),
            'date_cutoff': date_cutoff,
            'headers': data['headers'],
            'rows': data['rows'],
        }
        
        html = render_to_string('gold_loan/reports/pdf_template.html', context)
        response = HttpResponse(html, content_type='text/html')
        return response
