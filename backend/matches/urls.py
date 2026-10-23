from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('', views.match_list_view, name='list'),
    path('<int:match_id>/', views.match_detail_view, name='detail'),
    path('<int:match_id>/confirm/', views.confirm_match_view, name='confirm'),
    path('<int:match_id>/dismiss/', views.dismiss_match_view, name='dismiss'),
]
