from django.urls import path
from .friends_views import (
    FriendListView,
    FriendSearchView,
    FriendRequestCreateView,
    FriendRequestAcceptView,
    FriendRequestDeclineView,
    FriendRemoveView,
)

urlpatterns = [
    path("", FriendListView.as_view(), name="friends-list"),
    path("search/", FriendSearchView.as_view(), name="friends-search"),
    path("request/", FriendRequestCreateView.as_view(), name="friends-request-create"),
    path("<int:friendship_id>/accept/", FriendRequestAcceptView.as_view(), name="friends-accept"),
    path("<int:friendship_id>/decline/", FriendRequestDeclineView.as_view(), name="friends-decline"),
    path("<int:friendship_id>/", FriendRemoveView.as_view(), name="friends-remove"),
]
