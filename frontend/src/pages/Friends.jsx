import React, { useState, useEffect, useContext, useCallback } from 'react';
import { AuthContext } from '../context/AuthContext';
import { 
  getFriends, 
  searchUsers, 
  sendFriendRequest, 
  acceptFriendRequest, 
  declineFriendRequest, 
  removeFriend 
} from '../services/friends';
import Button from '../components/Button';
import './Friends.css';

const Friends = () => {
  const { user } = useContext(AuthContext);

  const [friends, setFriends] = useState([]);
  const [incomingRequests, setIncomingRequests] = useState([]);
  const [sentRequests, setSentRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [submittingAction, setSubmittingAction] = useState({});

  const fetchFriendships = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getFriends();
      setFriends(data.friends || []);
      setIncomingRequests(data.incoming_requests || []);
      setSentRequests(data.sent_requests || []);
    } catch (err) {
      console.error('Failed to load friends:', err);
      setError('Unable to load friends data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetchFriendships();
    }
  }, [user, fetchFriendships]);

  // Handle User Search
  const handleSearchSubmit = async (e) => {
    e?.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      setSearching(true);
      setSearchError('');
      const results = await searchUsers(searchQuery.trim());
      // Filter out self
      const filtered = results.filter((u) => u.username !== user?.username);
      setSearchResults(filtered);
    } catch (err) {
      console.error('Search error:', err);
      setSearchError('Error searching users.');
    } finally {
      setSearching(false);
    }
  };

  const handleSendRequest = async (username) => {
    try {
      setSubmittingAction((prev) => ({ ...prev, [username]: true }));
      setError('');
      setActionSuccess('');
      await sendFriendRequest(username);
      setActionSuccess(`Friend request sent to ${username}`);
      await fetchFriendships();
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to send friend request.';
      setError(msg);
    } finally {
      setSubmittingAction((prev) => ({ ...prev, [username]: false }));
    }
  };

  const handleAcceptRequest = async (friendshipId, username) => {
    try {
      setSubmittingAction((prev) => ({ ...prev, [friendshipId]: true }));
      setError('');
      setActionSuccess('');
      await acceptFriendRequest(friendshipId);
      setActionSuccess(`Accepted friend request from ${username}`);
      await fetchFriendships();
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to accept friend request.';
      setError(msg);
    } finally {
      setSubmittingAction((prev) => ({ ...prev, [friendshipId]: false }));
    }
  };

  const handleDeclineRequest = async (friendshipId, username) => {
    try {
      setSubmittingAction((prev) => ({ ...prev, [friendshipId]: true }));
      setError('');
      setActionSuccess('');
      await declineFriendRequest(friendshipId);
      setActionSuccess(`Declined request from ${username}`);
      await fetchFriendships();
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to decline friend request.';
      setError(msg);
    } finally {
      setSubmittingAction((prev) => ({ ...prev, [friendshipId]: false }));
    }
  };

  const handleRemoveFriend = async (friendshipId, username) => {
    if (!window.confirm(`Are you sure you want to remove ${username} from your friends?`)) {
      return;
    }
    try {
      setSubmittingAction((prev) => ({ ...prev, [friendshipId]: true }));
      setError('');
      setActionSuccess('');
      await removeFriend(friendshipId);
      setActionSuccess(`Removed ${username} from friends`);
      await fetchFriendships();
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to remove friend.';
      setError(msg);
    } finally {
      setSubmittingAction((prev) => ({ ...prev, [friendshipId]: false }));
    }
  };

  // Determine user relationship status for search results
  const getRelationshipStatus = (targetUsername) => {
    const isFriend = friends.some((f) => {
      const otherUser = f.user_username === user?.username ? f.friend_username : f.user_username;
      return otherUser === targetUsername;
    });
    if (isFriend) return 'FRIEND';

    const hasSent = sentRequests.some((r) => r.friend_username === targetUsername);
    if (hasSent) return 'SENT';

    const hasIncoming = incomingRequests.some((r) => r.user_username === targetUsername);
    if (hasIncoming) return 'INCOMING';

    return 'NONE';
  };

  // Extract initials for avatar
  const getInitials = (name) => {
    if (!name) return 'U';
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <div className="friends-page-container animate-fade-in">
      <div className="friends-header">
        <div className="friends-title-group">
          <h1 className="friends-title">Research Collaborators & Friends</h1>
          <p className="friends-subtitle">
            Connect with registered researchers to quickly invite them to projects and synthesis sessions.
          </p>
        </div>
      </div>

      {error && (
        <div className="friends-alert friends-alert-error" role="alert">
          <span>{error}</span>
          <button 
            type="button" 
            className="alert-dismiss-btn" 
            onClick={() => setError('')}
            aria-label="Dismiss error"
          >
            &times;
          </button>
        </div>
      )}

      {actionSuccess && (
        <div className="friends-alert friends-alert-success" role="status">
          <span>{actionSuccess}</span>
          <button 
            type="button" 
            className="alert-dismiss-btn" 
            onClick={() => setActionSuccess('')}
            aria-label="Dismiss message"
          >
            &times;
          </button>
        </div>
      )}

      {/* User Search Bar */}
      <section className="friends-search-section">
        <form className="friends-search-form" onSubmit={handleSearchSubmit}>
          <div className="search-input-wrapper">
            <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              type="text"
              className="friends-search-input"
              placeholder="Search registered users by username or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search registered users"
            />
          </div>
          <Button type="submit" disabled={searching || !searchQuery.trim()}>
            {searching ? 'Searching...' : 'Search'}
          </Button>
        </form>

        {searchError && <p className="friends-error-text">{searchError}</p>}

        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="search-results-panel">
            <h3 className="section-subheading">Search Results ({searchResults.length})</h3>
            <div className="friends-list">
              {searchResults.map((u) => {
                const rel = getRelationshipStatus(u.username);
                return (
                  <div key={u.id} className="friend-card">
                    <div className="friend-info">
                      <div className="friend-avatar" aria-hidden="true">
                        {getInitials(u.username)}
                      </div>
                      <div className="friend-meta">
                        <span className="friend-username">{u.username}</span>
                        {u.email && <span className="friend-email">{u.email}</span>}
                      </div>
                    </div>
                    <div className="friend-action">
                      {rel === 'FRIEND' && (
                        <span className="status-badge status-badge-accepted">Friend</span>
                      )}
                      {rel === 'SENT' && (
                        <span className="status-badge status-badge-pending">Request Sent</span>
                      )}
                      {rel === 'INCOMING' && (
                        <span className="status-badge status-badge-incoming">Requested You</span>
                      )}
                      {rel === 'NONE' && (
                        <Button
                          variant="secondary"
                          onClick={() => handleSendRequest(u.username)}
                          disabled={submittingAction[u.username]}
                        >
                          {submittingAction[u.username] ? 'Sending...' : 'Add Friend'}
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {/* Main Grid: My Friends & Requests */}
      <div className="friends-grid-layout">
        {/* Left Column: My Friends */}
        <section className="friends-section card-container">
          <div className="section-header">
            <h2 className="section-heading">
              My Friends
              <span className="count-pill">{friends.length}</span>
            </h2>
          </div>

          {loading ? (
            <p className="friends-empty-text">Loading contacts...</p>
          ) : friends.length === 0 ? (
            <div className="empty-friends-state">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
              <p>No friends added yet.</p>
              <span>Use the search bar above to connect with fellow researchers.</span>
            </div>
          ) : (
            <div className="friends-list">
              {friends.map((f) => {
                const otherUsername = f.user_username === user?.username ? f.friend_username : f.user_username;
                return (
                  <div key={f.id} className="friend-card">
                    <div className="friend-info">
                      <div className="friend-avatar" aria-hidden="true">
                        {getInitials(otherUsername)}
                      </div>
                      <div className="friend-meta">
                        <span className="friend-username">{otherUsername}</span>
                        <span className="friend-date">Connected {new Date(f.updated_at || f.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="friend-action">
                      <Button
                        variant="danger"
                        onClick={() => handleRemoveFriend(f.id, otherUsername)}
                        disabled={submittingAction[f.id]}
                        aria-label={`Remove ${otherUsername} from friends`}
                      >
                        {submittingAction[f.id] ? 'Removing...' : 'Remove'}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Right Column: Requests */}
        <div className="friends-requests-col">
          {/* Incoming Requests */}
          <section className="friends-section card-container">
            <div className="section-header">
              <h2 className="section-heading">
                Incoming Requests
                <span className="count-pill">{incomingRequests.length}</span>
              </h2>
            </div>

            {loading ? (
              <p className="friends-empty-text">Checking requests...</p>
            ) : incomingRequests.length === 0 ? (
              <p className="friends-empty-text">No incoming friend requests.</p>
            ) : (
              <div className="friends-list">
                {incomingRequests.map((req) => (
                  <div key={req.id} className="friend-card">
                    <div className="friend-info">
                      <div className="friend-avatar" aria-hidden="true">
                        {getInitials(req.user_username)}
                      </div>
                      <div className="friend-meta">
                        <span className="friend-username">{req.user_username}</span>
                        <span className="friend-date">Sent request</span>
                      </div>
                    </div>
                    <div className="friend-action-group">
                      <Button
                        onClick={() => handleAcceptRequest(req.id, req.user_username)}
                        disabled={submittingAction[req.id]}
                        aria-label={`Accept request from ${req.user_username}`}
                      >
                        Accept
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => handleDeclineRequest(req.id, req.user_username)}
                        disabled={submittingAction[req.id]}
                        aria-label={`Decline request from ${req.user_username}`}
                      >
                        Decline
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Sent Requests */}
          <section className="friends-section card-container">
            <div className="section-header">
              <h2 className="section-heading">
                Sent Requests
                <span className="count-pill">{sentRequests.length}</span>
              </h2>
            </div>

            {loading ? (
              <p className="friends-empty-text">Checking sent requests...</p>
            ) : sentRequests.length === 0 ? (
              <p className="friends-empty-text">No pending sent requests.</p>
            ) : (
              <div className="friends-list">
                {sentRequests.map((req) => (
                  <div key={req.id} className="friend-card">
                    <div className="friend-info">
                      <div className="friend-avatar" aria-hidden="true">
                        {getInitials(req.friend_username)}
                      </div>
                      <div className="friend-meta">
                        <span className="friend-username">{req.friend_username}</span>
                        <span className="friend-date">Awaiting acceptance</span>
                      </div>
                    </div>
                    <div className="friend-action">
                      <span className="status-badge status-badge-pending">Pending</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};

export default Friends;
