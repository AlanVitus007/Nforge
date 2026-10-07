from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import Friendship
from .serializers import SafeUserSerializer, FriendshipSerializer


class FriendListView(APIView):
    """
    GET /api/friends/
    Lists current friends, incoming pending requests, and outgoing pending requests.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Accepted friendships where user is either sender or receiver
        accepted = Friendship.objects.filter(
            Q(user=user) | Q(friend=user),
            status=Friendship.STATUS_ACCEPTED
        ).select_related("user", "friend")

        friends_list = []
        for f in accepted:
            other_user = f.friend if f.user == user else f.user
            friends_list.append({
                "id": f.id,
                "friendship_id": f.id,
                "user_id": f.user_id,
                "user_username": f.user.username,
                "friend_id": f.friend_id,
                "friend_username": f.friend.username,
                "other_username": other_user.username,
                "user": SafeUserSerializer(other_user).data,
                "created_at": f.created_at,
                "updated_at": f.updated_at,
            })

        # Incoming pending requests sent TO this user
        incoming = Friendship.objects.filter(
            friend=user,
            status=Friendship.STATUS_PENDING
        ).select_related("user")

        incoming_list = [
            {
                "id": f.id,
                "friendship_id": f.id,
                "user_id": f.user_id,
                "user_username": f.user.username,
                "from_user": SafeUserSerializer(f.user).data,
                "created_at": f.created_at,
            }
            for f in incoming
        ]

        # Outgoing pending requests sent BY this user
        outgoing = Friendship.objects.filter(
            user=user,
            status=Friendship.STATUS_PENDING
        ).select_related("friend")

        outgoing_list = [
            {
                "id": f.id,
                "friendship_id": f.id,
                "friend_id": f.friend_id,
                "friend_username": f.friend.username,
                "to_user": SafeUserSerializer(f.friend).data,
                "created_at": f.created_at,
                "status": f.status,
            }
            for f in outgoing
        ]

        return Response({
            "friends": friends_list,
            "incoming": incoming_list,
            "incoming_requests": incoming_list,
            "outgoing": outgoing_list,
            "sent_requests": outgoing_list,
        })


class FriendSearchView(APIView):
    """
    GET /api/friends/search/?q=<query>
    Searches registered users and returns their friendship status relative to the current user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query or len(query) < 1:
            return Response([])

        users = (
            User.objects.filter(
                Q(username__icontains=query) | Q(email__icontains=query),
                is_active=True,
            )
            .exclude(id=request.user.id)
            .order_by("username")[:20]
        )

        user_ids = [u.id for u in users]
        current_user = request.user

        # Fetch existing relationships in either direction
        existing_relations = Friendship.objects.filter(
            Q(user=current_user, friend_id__in=user_ids) |
            Q(friend=current_user, user_id__in=user_ids)
        )

        relation_map = {}
        for rel in existing_relations:
            other_id = rel.friend_id if rel.user_id == current_user.id else rel.user_id
            relation_map[other_id] = rel

        results = []
        for u in users:
            rel = relation_map.get(u.id)
            friendship_status = "NONE"
            friendship_id = None

            if rel:
                friendship_id = rel.id
                if rel.status == Friendship.STATUS_ACCEPTED:
                    friendship_status = "FRIEND"
                elif rel.status == Friendship.STATUS_PENDING:
                    friendship_status = "OUTGOING" if rel.user_id == current_user.id else "INCOMING"
                elif rel.status == Friendship.STATUS_DECLINED:
                    friendship_status = "DECLINED"

            results.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "friendship_status": friendship_status,
                "friendship_id": friendship_id,
            })

        return Response(results)


class FriendRequestCreateView(APIView):
    """
    POST /api/friends/request/
    Sends a friend request to a target user by username or user_id.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        username = request.data.get("username") or request.data.get("friend_username")
        user_id = request.data.get("user_id")

        if not username and not user_id:
            msg = "Username or user_id is required."
            return Response(
                {"detail": msg, "error": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_id:
            target_user = User.objects.filter(id=user_id, is_active=True).first()
        else:
            target_user = User.objects.filter(username=str(username).strip(), is_active=True).first()

        if not target_user:
            msg = f"User '{username or user_id}' does not exist."
            return Response(
                {"detail": msg, "error": msg},
                status=status.HTTP_404_NOT_FOUND,
            )

        if target_user.id == request.user.id:
            msg = "You cannot send a friend request to yourself."
            return Response(
                {"detail": msg, "error": msg},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check existing relationship in either direction
        existing = Friendship.objects.filter(
            Q(user=request.user, friend=target_user) |
            Q(user=target_user, friend=request.user)
        ).first()

        if existing:
            if existing.status == Friendship.STATUS_ACCEPTED:
                msg = "You are already friends with this user."
                return Response(
                    {"detail": msg, "error": msg},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if existing.status == Friendship.STATUS_PENDING:
                msg = "A friend request is already pending between you and this user."
                return Response(
                    {"detail": msg, "error": msg},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # If declined previously, reset to pending from current user
            existing.user = request.user
            existing.friend = target_user
            existing.status = Friendship.STATUS_PENDING
            existing.save()
            return Response(
                FriendshipSerializer(existing).data,
                status=status.HTTP_201_CREATED,
            )

        friendship = Friendship.objects.create(
            user=request.user,
            friend=target_user,
            status=Friendship.STATUS_PENDING,
        )
        return Response(
            FriendshipSerializer(friendship).data,
            status=status.HTTP_201_CREATED,
        )


class FriendRequestAcceptView(APIView):
    """
    POST /api/friends/<int:friendship_id>/accept/
    Accepts an incoming friend request.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, friendship_id):
        friendship = get_object_or_404(Friendship, id=friendship_id)

        if friendship.friend_id != request.user.id:
            return Response(
                {"detail": "You do not have permission to accept this friend request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if friendship.status != Friendship.STATUS_PENDING:
            return Response(
                {"detail": f"Cannot accept request with status '{friendship.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        friendship.status = Friendship.STATUS_ACCEPTED
        friendship.save()
        return Response(
            {"detail": "Friend request accepted successfully.", "friendship": FriendshipSerializer(friendship).data},
            status=status.HTTP_200_OK,
        )


class FriendRequestDeclineView(APIView):
    """
    POST /api/friends/<int:friendship_id>/decline/
    Declines an incoming friend request.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, friendship_id):
        friendship = get_object_or_404(Friendship, id=friendship_id)

        if friendship.friend_id != request.user.id:
            return Response(
                {"detail": "You do not have permission to decline this friend request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if friendship.status != Friendship.STATUS_PENDING:
            return Response(
                {"detail": f"Cannot decline request with status '{friendship.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        friendship.status = Friendship.STATUS_DECLINED
        friendship.save()
        return Response(
            {"detail": "Friend request declined."},
            status=status.HTTP_200_OK,
        )


class FriendRemoveView(APIView):
    """
    DELETE /api/friends/<int:friendship_id>/
    Removes an accepted friend or cancels a pending outgoing request.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, friendship_id):
        friendship = get_object_or_404(Friendship, id=friendship_id)

        if request.user.id not in (friendship.user_id, friendship.friend_id):
            return Response(
                {"detail": "You do not have permission to remove this friend."},
                status=status.HTTP_403_FORBIDDEN,
            )

        friendship.delete()
        return Response(
            {"detail": "Friend removed successfully."},
            status=status.HTTP_200_OK,
        )
