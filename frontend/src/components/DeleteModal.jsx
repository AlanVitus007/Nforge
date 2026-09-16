import React from 'react';
import './DeleteModal.css';

/**
 * Reusable confirmation modal for destructive actions.
 *
 * Props:
 *   isOpen       – boolean, controls visibility
 *   onClose      – fn, called when cancelled or overlay clicked
 *   onConfirm    – fn, called when "Delete" confirmed
 *   title        – string, modal heading
 *   message      – ReactNode, body message
 *   warning      – string, secondary warning line (optional)
 *   isDeleting   – boolean, shows loading state on confirm button
 */
const DeleteModal = ({
    isOpen,
    onClose,
    onConfirm,
    title = 'Are you sure?',
    message,
    warning = 'This action cannot be undone.',
    isDeleting = false,
}) => {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose} role="presentation">
            <div
                className="delete-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="delete-modal-title"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Icon */}
                <div className="modal-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
                        <path d="M10 11v6"></path>
                        <path d="M14 11v6"></path>
                        <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path>
                    </svg>
                </div>

                <h2 id="delete-modal-title" className="modal-title">{title}</h2>

                {message && <p className="modal-message">{message}</p>}

                {warning && <p className="modal-warning">{warning}</p>}

                <div className="modal-actions">
                    <button
                        className="modal-cancel-btn"
                        onClick={onClose}
                        disabled={isDeleting}
                    >
                        Cancel
                    </button>
                    <button
                        className="modal-confirm-btn"
                        onClick={onConfirm}
                        disabled={isDeleting}
                    >
                        {isDeleting ? 'Deleting…' : 'Delete'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DeleteModal;
