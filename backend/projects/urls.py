from django.urls import path
from .views import (
    ProjectListCreateView,
    ProjectDetailView,
    ProjectInviteMemberView,
    ProjectMemberListView,
    ProjectMemberDetailView,
    ProjectLeaveView,
    UserInvitationListView,
    InvitationAcceptView,
    InvitationDeclineView,
    InvitationCancelView,
)

urlpatterns = [
    # Invitations endpoints
    path('invitations/', UserInvitationListView.as_view(), name='user-invitations'),
    path('invitations/<int:invitation_id>/accept/', InvitationAcceptView.as_view(), name='invitation-accept'),
    path('invitations/<int:invitation_id>/decline/', InvitationDeclineView.as_view(), name='invitation-decline'),
    path('invitations/<int:invitation_id>/cancel/', InvitationCancelView.as_view(), name='invitation-cancel'),

    # Project member & collaboration endpoints
    path('<int:project_id>/members/invite/', ProjectInviteMemberView.as_view(), name='project-member-invite'),
    path('<int:project_id>/members/', ProjectMemberListView.as_view(), name='project-members-list'),
    path('<int:project_id>/members/<int:user_id>/', ProjectMemberDetailView.as_view(), name='project-member-delete'),
    path('<int:project_id>/leave/', ProjectLeaveView.as_view(), name='project-leave'),

    # Existing project CRUD endpoints
    path('', ProjectListCreateView.as_view(), name='project-list-create'),
    path('<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
]
