from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    # Submit a claim for a specific item
    path('item/<int:item_id>/submit/', views.submit_claim_view, name='submit_claim'),

    # View all claims for a specific item (reporter / admin)
    path('item/<int:item_id>/', views.item_claims_view, name='item_claims'),

    # My claims list (claimant)
    path('my/', views.my_claims_view, name='my_claims'),

    # Admin: all claims list
    path('manage/', views.claim_list_view, name='claim_list'),

    # Claim detail
    path('<int:claim_id>/', views.claim_detail_view, name='claim_detail'),

    # Withdraw a pending claim
    path('<int:claim_id>/withdraw/', views.withdraw_claim_view, name='withdraw_claim'),

    # Review (approve/reject) a claim
    path('<int:claim_id>/review/', views.review_claim_view, name='review_claim'),
]
