import { useEffect, useState, useContext, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { askResearchSession } from '../services/ai';
import { AuthContext } from '../context/AuthContext';
import EvidenceSource from '../components/EvidenceSource';
import DeleteModal from '../components/DeleteModal';
import MarkdownRenderer from '../components/MarkdownRenderer';
import { getProjectMembers, determineUserRole } from '../services/collaboration';
import NotebookButton from '../components/notebook/NotebookButton';
import PaperNotebookPanel from '../components/notebook/PaperNotebookPanel';
import './ResearchWorkspace.css';

/**
 * Helper to safely parse and detect structured multi-paper comparison JSON for historical messages.
 * Enriches evidence paper titles.
 */
function parseStructuredComparison(content, papers = []) {
    let parsed = null;

    if (content && typeof content === 'object') {
        parsed = content;
    } else if (typeof content === 'string') {
        const trimmed = content.trim();
        if (trimmed.startsWith('{') || trimmed.startsWith('```')) {
            let jsonStr = trimmed;
            if (jsonStr.startsWith('```')) {
                jsonStr = jsonStr.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
            }
            try {
                parsed = JSON.parse(jsonStr);
            } catch {
                return null;
            }
        }
    }

    if (
        parsed &&
        typeof parsed === 'object' &&
        (parsed.overall_synthesis ||
         Array.isArray(parsed.similarities) ||
         Array.isArray(parsed.differences) ||
         Array.isArray(parsed.methodology_comparison) ||
         Array.isArray(parsed.findings_comparison) ||
         Array.isArray(parsed.research_gaps))
    ) {
        if (papers && papers.length > 0) {
            const paperMap = {};
            papers.forEach((p) => {
                paperMap[p.id] = p.title;
            });

            const enrichSources = (list) => {
                if (!Array.isArray(list)) return;
                list.forEach((item) => {
                    if (item && Array.isArray(item.sources)) {
                        item.sources.forEach((src) => {
                            if (src && !src.paper_title && src.paper_id && paperMap[src.paper_id]) {
                                src.paper_title = paperMap[src.paper_id];
                            }
                        });
                    }
                });
            };

            enrichSources(parsed.similarities);
            enrichSources(parsed.differences);
            enrichSources(parsed.methodology_comparison);
            enrichSources(parsed.findings_comparison);
            enrichSources(parsed.research_gaps);
        }
        return parsed;
    }
    return null;
}

/**
 * Helper to safely parse and detect structured multi-paper research gap analysis JSON for historical messages.
 */
function parseStructuredGapAnalysis(content, papers = []) {
    let parsed = null;

    if (content && typeof content === 'object') {
        parsed = content;
    } else if (typeof content === 'string') {
        const trimmed = content.trim();
        if (trimmed.startsWith('{') || trimmed.startsWith('```')) {
            let jsonStr = trimmed;
            if (jsonStr.startsWith('```')) {
                jsonStr = jsonStr.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
            }
            try {
                parsed = JSON.parse(jsonStr);
            } catch {
                return null;
            }
        }
    }

    if (
        parsed &&
        typeof parsed === 'object' &&
        (parsed.overall_assessment ||
         Array.isArray(parsed.common_limitations) ||
         Array.isArray(parsed.methodological_gaps) ||
         Array.isArray(parsed.dataset_population_gaps) ||
         Array.isArray(parsed.understudied_areas) ||
         Array.isArray(parsed.contradictions_inconsistencies) ||
         Array.isArray(parsed.unanswered_research_questions) ||
         Array.isArray(parsed.future_research_directions))
    ) {
        if (papers && papers.length > 0) {
            const paperMap = {};
            papers.forEach((p) => {
                paperMap[p.id] = p.title;
            });

            const enrichSources = (list) => {
                if (!Array.isArray(list)) return;
                list.forEach((item) => {
                    if (item && Array.isArray(item.sources)) {
                        item.sources.forEach((src) => {
                            if (src && !src.paper_title && src.paper_id && paperMap[src.paper_id]) {
                                src.paper_title = paperMap[src.paper_id];
                            }
                        });
                    }
                });
            };

            enrichSources(parsed.common_limitations);
            enrichSources(parsed.methodological_gaps);
            enrichSources(parsed.dataset_population_gaps);
            enrichSources(parsed.understudied_areas);
            enrichSources(parsed.contradictions_inconsistencies);
            enrichSources(parsed.unanswered_research_questions);
            enrichSources(parsed.future_research_directions);
        }
        return parsed;
    }
    return null;
}

/**
 * Helper to safely parse and detect structured cross-paper thematic analysis JSON for historical messages.
 */
function parseStructuredThematicAnalysis(content, papers = []) {
    let parsed = null;

    if (content && typeof content === 'object') {
        parsed = content;
    } else if (typeof content === 'string') {
        const trimmed = content.trim();
        if (trimmed.startsWith('{') || trimmed.startsWith('```')) {
            let jsonStr = trimmed;
            if (jsonStr.startsWith('```')) {
                jsonStr = jsonStr.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
            }
            try {
                parsed = JSON.parse(jsonStr);
            } catch {
                return null;
            }
        }
    }

    if (
        parsed &&
        typeof parsed === 'object' &&
        (parsed.overall_synthesis || Array.isArray(parsed.themes))
    ) {
        if (papers && papers.length > 0) {
            const paperMap = {};
            papers.forEach((p) => {
                paperMap[p.id] = p.title;
            });

            if (Array.isArray(parsed.themes)) {
                parsed.themes.forEach((th) => {
                    if (th && Array.isArray(th.papers)) {
                        th.papers.forEach((pEntry) => {
                            if (pEntry) {
                                const pTitle = pEntry.paper_title || paperMap[pEntry.paper_id];
                                if (pTitle && !pEntry.paper_title) {
                                    pEntry.paper_title = pTitle;
                                }
                                if (Array.isArray(pEntry.sources)) {
                                    pEntry.sources.forEach((src) => {
                                        if (src) {
                                            if (!src.paper_id && pEntry.paper_id) {
                                                src.paper_id = pEntry.paper_id;
                                            }
                                            if (!src.paper_title && (src.paper_id && paperMap[src.paper_id])) {
                                                src.paper_title = paperMap[src.paper_id];
                                            } else if (!src.paper_title && pTitle) {
                                                src.paper_title = pTitle;
                                            }
                                        }
                                    });
                                }
                            }
                        });
                    }
                });
            }
        }
        return parsed;
    }
    return null;
}

/**
 * Helper to safely parse and detect structured cross-paper research trend analysis JSON for historical messages.
 */
function parseStructuredTrendAnalysis(content, papers = []) {
    let parsed = null;

    if (content && typeof content === 'object') {
        parsed = content;
    } else if (typeof content === 'string') {
        const trimmed = content.trim();
        if (trimmed.startsWith('{') || trimmed.startsWith('```')) {
            let jsonStr = trimmed;
            if (jsonStr.startsWith('```')) {
                jsonStr = jsonStr.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
            }
            try {
                parsed = JSON.parse(jsonStr);
            } catch {
                return null;
            }
        }
    }

    if (
        parsed &&
        typeof parsed === 'object' &&
        (parsed.overall_trend ||
         Array.isArray(parsed.research_evolution) ||
         Array.isArray(parsed.emerging_directions) ||
         Array.isArray(parsed.methodology_evolution) ||
         Array.isArray(parsed.future_directions))
    ) {
        if (papers && papers.length > 0) {
            const paperMap = {};
            papers.forEach((p) => {
                paperMap[p.id] = p.title;
            });

            if (Array.isArray(parsed.research_evolution)) {
                parsed.research_evolution.forEach((ev) => {
                    if (ev && Array.isArray(ev.papers)) {
                        ev.papers.forEach((pEntry) => {
                            if (pEntry) {
                                const pTitle = pEntry.paper_title || paperMap[pEntry.paper_id];
                                if (pTitle && !pEntry.paper_title) {
                                    pEntry.paper_title = pTitle;
                                }
                                if (Array.isArray(pEntry.sources)) {
                                    pEntry.sources.forEach((src) => {
                                        if (src) {
                                            if (!src.paper_id && pEntry.paper_id) {
                                                src.paper_id = pEntry.paper_id;
                                            }
                                            if (!src.paper_title && (src.paper_id && paperMap[src.paper_id])) {
                                                src.paper_title = paperMap[src.paper_id];
                                            } else if (!src.paper_title && pTitle) {
                                                src.paper_title = pTitle;
                                            }
                                        }
                                    });
                                }
                            }
                        });
                    }
                });
            }

            const otherSections = [
                parsed.emerging_directions,
                parsed.methodology_evolution,
                parsed.future_directions
            ];
            otherSections.forEach((sectionList) => {
                if (Array.isArray(sectionList)) {
                    sectionList.forEach((item) => {
                        if (item && Array.isArray(item.sources)) {
                            item.sources.forEach((src) => {
                                if (src && !src.paper_title && src.paper_id && paperMap[src.paper_id]) {
                                    src.paper_title = paperMap[src.paper_id];
                                }
                            });
                        }
                    });
                }
            });
        }
        return parsed;
    }
    return null;
}

/**
 * Helper to generate a concise, safe auto-title from the user's first research question.
 */
function generateAutoTitle(text) {
    if (!text || typeof text !== 'string') return 'Research Session';
    const cleaned = text.replace(/[\r\n\t]+/g, ' ').trim();
    if (!cleaned) return 'Research Session';
    if (cleaned.length <= 50) return cleaned;
    return cleaned.slice(0, 47).trim() + '...';
}

/**
 * Helper to format session updated date/time.
 */
function formatSessionTime(isoString) {
    if (!isoString) return '';
    try {
        const date = new Date(isoString);
        const now = new Date();
        const isToday = date.toDateString() === now.toDateString();
        if (isToday) {
            return `Today, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        }
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
        return '';
    }
}

/**
 * Research prompt shortcuts for Multi-Paper session research.
 */
const SESSION_RESEARCH_SHORTCUTS = [
    {
        label: 'Summarize the research',
        prompt: 'Summarize the research and synthesize the main contributions across these papers.'
    },
    {
        label: 'Explain methodologies',
        prompt: 'Explain the methodologies used across these papers, comparing their approaches, data, and evaluation techniques.'
    },
    {
        label: 'Identify key findings',
        prompt: 'Identify and synthesize the key findings and results across these papers.'
    },
    {
        label: 'Identify limitations',
        prompt: 'Identify the main limitations and caveats evident across these papers.'
    },
    {
        label: 'Suggest future directions',
        prompt: 'Suggest possible future research directions based on the collective findings and limitations across these papers.'
    }
];

function ResearchWorkspace() {
    const { projectId } = useParams();
    const navigate = useNavigate();
    const { user, loading: authLoading } = useContext(AuthContext);

    const [project, setProject] = useState(null);
    const [projectPapers, setProjectPapers] = useState([]);
    const [sessions, setSessions] = useState([]);
    const [activeSessionId, setActiveSessionId] = useState(null);
    const [activeSession, setActiveSession] = useState(null);
    const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

    // Papers Management Modal state
    const [isPapersModalOpen, setIsPapersModalOpen] = useState(false);
    const [selectedModalPaperIds, setSelectedModalPaperIds] = useState([]);
    const [savingPapers, setSavingPapers] = useState(false);
    const [removingPaperId, setRemovingPaperId] = useState(null);

    // Paper-Specific Notebook state
    const [isNotebookOpen, setIsNotebookOpen] = useState(false);
    const [notebookNotesCount, setNotebookNotesCount] = useState(0);

    // Live Multi-Paper Session Research Chat State
    const [questionText, setQuestionText] = useState('');
    const [loadingAsk, setLoadingAsk] = useState(false);
    const [askError, setAskError] = useState('');

    // Loading & Action states
    const [userRole, setUserRole] = useState("VIEWER");
    const isViewer = userRole === "VIEWER";

    const [loadingList, setLoadingList] = useState(true);
    const [loadingSession, setLoadingSession] = useState(false);
    const [creatingSession, setCreatingSession] = useState(false);
    const [isRenaming, setIsRenaming] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    // Errors
    const [listError, setListError] = useState('');
    const [sessionError, setSessionError] = useState('');
    const [actionError, setActionError] = useState('');
    const [renameError, setRenameError] = useState('');

    // Menu and Modals
    const [openMenuId, setOpenMenuId] = useState(null);
    const [renamingSessionId, setRenamingSessionId] = useState(null);
    const [renameTitle, setRenameTitle] = useState('');
    const [deletingSession, setDeletingSession] = useState(null);

    const chatScrollRef = useRef(null);
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);
    const currentSelectIdRef = useRef(null);
    const [isNearBottom, setIsNearBottom] = useState(true);
    const isNearBottomRef = useRef(true);
    const lastScrolledSessionIdRef = useRef(null);
    const prevMessageCountRef = useRef(0);

    // Auto-resize composer textarea height between ~65px default (min 55px) and 140px
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            const scrollH = textareaRef.current.scrollHeight;
            const targetH = scrollH <= 72 ? 65 : Math.min(scrollH, 140);
            textareaRef.current.style.height = `${targetH}px`;
        }
    }, [questionText]);

    // Redirect if unauthenticated
    useEffect(() => {
        if (!authLoading && !user) {
            navigate('/login');
        }
    }, [user, authLoading, navigate]);

    const scrollToBottom = useCallback((smooth = true) => {
        requestAnimationFrame(() => {
            if (chatScrollRef.current) {
                if (smooth) {
                    chatScrollRef.current.scrollTo({
                        top: chatScrollRef.current.scrollHeight,
                        behavior: 'smooth'
                    });
                } else {
                    chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
                }
            } else if (messagesEndRef.current) {
                messagesEndRef.current.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
            }
        });
    }, []);

    const handleConversationScroll = useCallback(() => {
        if (!chatScrollRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = chatScrollRef.current;
        const distanceFromBottom = scrollHeight - (scrollTop + clientHeight);
        const nearBottom = distanceFromBottom <= 120;
        setIsNearBottom(nearBottom);
        isNearBottomRef.current = nearBottom;
    }, []);

    const activeSessionKey = activeSession?.id;
    const sessionMessagesCount = activeSession?.messages?.length || 0;

    // Initial session load & session switching: instantly position at latest message
    useEffect(() => {
        if (!loadingSession && activeSessionKey) {
            if (lastScrolledSessionIdRef.current !== activeSessionKey) {
                lastScrolledSessionIdRef.current = activeSessionKey;
                prevMessageCountRef.current = sessionMessagesCount;
                setIsNearBottom(true);
                isNearBottomRef.current = true;

                const scrollToEnd = () => {
                    if (chatScrollRef.current) {
                        chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
                    }
                };

                requestAnimationFrame(scrollToEnd);
                const timer1 = setTimeout(scrollToEnd, 60);
                const timer2 = setTimeout(scrollToEnd, 180);
                return () => {
                    clearTimeout(timer1);
                    clearTimeout(timer2);
                };
            }
        }
    }, [activeSessionKey, loadingSession, sessionMessagesCount]);

    // When new messages are appended to active session, smoothly scroll down
    useEffect(() => {
        if (!activeSessionKey || loadingSession) return;
        if (lastScrolledSessionIdRef.current === activeSessionKey && sessionMessagesCount > prevMessageCountRef.current) {
            if (isNearBottomRef.current) {
                scrollToBottom(true);
            }
        }
        prevMessageCountRef.current = sessionMessagesCount;
    }, [activeSessionKey, loadingSession, sessionMessagesCount, scrollToBottom]);

    // Ensure analyzing banner is visible when user sends a question
    useEffect(() => {
        if (loadingAsk && chatScrollRef.current) {
            scrollToBottom(true);
        }
    }, [loadingAsk, scrollToBottom]);

    // Select and open an existing session
    const handleSelectSession = useCallback(async (sessionId) => {
        currentSelectIdRef.current = sessionId;
        setIsMobileSidebarOpen(false);
        try {
            setActiveSessionId(sessionId);
            setActiveSession(null);
            lastScrolledSessionIdRef.current = null;
            setLoadingSession(true);
            setSessionError('');
            setAskError('');
            setQuestionText('');

            const res = await api.get(`/ai/sessions/${sessionId}/`);

            if (currentSelectIdRef.current !== sessionId) return;

            const sessionData = res.data;
            setActiveSession(sessionData);
        } catch (err) {
            if (currentSelectIdRef.current !== sessionId) return;
            if (err.response?.status === 401) {
                setSessionError('Authentication required.');
            } else if (err.response?.status === 403) {
                setSessionError('You do not have access to this research session.');
            } else if (err.response?.status === 404) {
                setSessionError('Research session not found.');
            } else {
                setSessionError(err.response?.data?.error || 'Failed to load session conversation.');
            }
        } finally {
            if (currentSelectIdRef.current === sessionId) {
                setLoadingSession(false);
            }
        }
    }, []);

    // Fetch project info, project papers, and initial session list
    useEffect(() => {
        if (!projectId) return;

        const loadProjectAndSessions = async () => {
            try {
                setLoadingList(true);
                setListError('');

                try {
                    const projRes = await api.get(`/projects/${projectId}/`);
                    const projData = projRes.data;
                    setProject(projData);

                    if (user && projData.owner === user.username) {
                        setUserRole("OWNER");
                    } else {
                        try {
                            const members = await getProjectMembers(projectId);
                            const role = determineUserRole(projData, user, members);
                            setUserRole(role || "VIEWER");
                        } catch {
                            setUserRole("VIEWER");
                        }
                    }
                } catch {
                    // Non-fatal
                }

                try {
                    const papersRes = await api.get(`/projects/${projectId}/papers/`);
                    setProjectPapers(papersRes.data || []);
                } catch {
                    // Non-fatal
                }

                const sessRes = await api.get(`/ai/sessions/?project_id=${projectId}`);
                const fetchedSessions = sessRes.data || [];
                setSessions(fetchedSessions);

                if (fetchedSessions.length > 0) {
                    handleSelectSession(fetchedSessions[0].id);
                }
            } catch (err) {
                if (err.response?.status === 401) {
                    setListError('Authentication required.');
                } else if (err.response?.status === 403) {
                    setListError('You do not have access to this research session.');
                } else if (err.response?.status === 404) {
                    setListError('Project not found.');
                } else {
                    setListError(err.response?.data?.error || 'Failed to load research sessions.');
                }
            } finally {
                setLoadingList(false);
            }
        };

        loadProjectAndSessions();
    }, [projectId, user, handleSelectSession]);

    // Close menu when clicking outside
    useEffect(() => {
        const handleGlobalClick = () => setOpenMenuId(null);
        window.addEventListener('click', handleGlobalClick);
        return () => window.removeEventListener('click', handleGlobalClick);
    }, []);

    // Create a new session
    const handleCreateSession = async () => {
        if (creatingSession || isViewer) return;
        setIsMobileSidebarOpen(false);
        try {
            setCreatingSession(true);
            setActionError('');

            const res = await api.post('/ai/sessions/', {
                project_id: parseInt(projectId, 10),
                title: 'New Research Session'
            });

            const newSession = res.data;
            setSessions((prev) => [newSession, ...prev]);
            currentSelectIdRef.current = newSession.id;
            setActiveSessionId(newSession.id);
            setActiveSession({
                ...newSession,
                messages: []
            });
            setQuestionText('');
            setAskError('');
        } catch (err) {
            setActionError(err.response?.data?.error || 'Failed to create research session.');
        } finally {
            setCreatingSession(false);
        }
    };

    // Rename session
    const startRename = (session, e) => {
        if (isViewer) return;
        if (e) e.stopPropagation();
        setRenamingSessionId(session.id);
        setRenameTitle(session.title || '');
        setRenameError('');
        setOpenMenuId(null);
    };

    const cancelRename = () => {
        setRenamingSessionId(null);
        setRenameError('');
    };

    const handleSaveRename = async (sessionId, e) => {
        if (isViewer) return;
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        const trimmed = renameTitle.trim();
        if (!trimmed) {
            setRenameError('Title cannot be empty.');
            return;
        }

        try {
            setIsRenaming(true);
            setRenameError('');
            setActionError('');

            const res = await api.patch(`/ai/sessions/${sessionId}/`, {
                title: trimmed
            });
            const updated = res.data;

            setSessions((prev) =>
                prev.map((s) => (s.id === sessionId ? { ...s, title: updated.title, updated_at: updated.updated_at } : s))
            );

            if (activeSessionId === sessionId) {
                setActiveSession((prev) => (prev ? { ...prev, title: updated.title, updated_at: updated.updated_at } : prev));
            }
            setRenamingSessionId(null);
        } catch (err) {
            const errorMsg = err.response?.data?.error || 'Failed to rename session.';
            setRenameError(errorMsg);
            setActionError(errorMsg);
        } finally {
            setIsRenaming(false);
        }
    };

    // Delete session
    const openDeleteModal = (session, e) => {
        if (isViewer) return;
        if (e) e.stopPropagation();
        setDeletingSession(session);
        setOpenMenuId(null);
    };

    const handleConfirmDelete = async () => {
        if (!deletingSession || isDeleting || isViewer) return;
        const targetId = deletingSession.id;
        try {
            setIsDeleting(true);
            setActionError('');

            await api.delete(`/ai/sessions/${targetId}/`);

            setSessions((prev) => {
                const remaining = prev.filter((s) => s.id !== targetId);
                if (activeSessionId === targetId) {
                    if (remaining.length > 0) {
                        handleSelectSession(remaining[0].id);
                    } else {
                        currentSelectIdRef.current = null;
                        setActiveSessionId(null);
                        setActiveSession(null);
                    }
                }
                return remaining;
            });
            setDeletingSession(null);
        } catch (err) {
            setActionError(err.response?.data?.error || 'Failed to delete session.');
        } finally {
            setIsDeleting(false);
        }
    };

    // Open Paper Selection Modal
    const openAddPapersModal = () => {
        if (isViewer) return;
        const currentPaperIds = (activeSession?.papers || []).map((p) => p.id);
        setSelectedModalPaperIds(currentPaperIds);
        setIsPapersModalOpen(true);
    };

    // Toggle Paper Selection in Modal
    const togglePaperSelection = (paperId) => {
        setSelectedModalPaperIds((prev) =>
            prev.includes(paperId) ? prev.filter((id) => id !== paperId) : [...prev, paperId]
        );
    };

    // Save Papers to Session via PATCH
    const handleSaveSessionPapers = async () => {
        if (!activeSessionId || isViewer) return;
        try {
            setSavingPapers(true);
            setActionError('');

            const res = await api.patch(`/ai/sessions/${activeSessionId}/`, {
                papers: selectedModalPaperIds
            });
            const updated = res.data;

            setActiveSession((prev) => ({
                ...prev,
                papers: updated.papers,
                updated_at: updated.updated_at
            }));

            setSessions((prev) =>
                prev.map((s) => (s.id === activeSessionId ? { ...s, papers: updated.papers, updated_at: updated.updated_at } : s))
            );

            setIsPapersModalOpen(false);
        } catch (err) {
            setActionError(err.response?.data?.error || 'Failed to update session papers.');
        } finally {
            setSavingPapers(false);
        }
    };

    // Remove Paper directly from session
    const handleRemovePaperFromSession = async (paperIdToRemove) => {
        if (removingPaperId || !activeSessionId || !activeSession?.papers || isViewer) return;
        const remainingIds = activeSession.papers.filter((p) => p.id !== paperIdToRemove).map((p) => p.id);

        try {
            setRemovingPaperId(paperIdToRemove);
            setActionError('');
            const res = await api.patch(`/ai/sessions/${activeSessionId}/`, {
                papers: remainingIds
            });
            const updated = res.data;

            setActiveSession((prev) => ({
                ...prev,
                papers: updated.papers,
                updated_at: updated.updated_at
            }));

            setSessions((prev) =>
                prev.map((s) => (s.id === activeSessionId ? { ...s, papers: updated.papers, updated_at: updated.updated_at } : s))
            );
        } catch (err) {
            setActionError(err.response?.data?.error || 'Failed to remove paper from session.');
        } finally {
            setRemovingPaperId(null);
        }
    };

    // Send Multi-Paper Research Question via POST /api/ai/research-ask/
    const handleSendQuestion = async () => {
        if (isViewer || loadingAsk) return;
        const trimmed = questionText.trim();
        if (!trimmed) return;
        if (!activeSessionId) return;

        if (!activeSession?.papers || activeSession.papers.length === 0) {
            setAskError('Add research papers to this session to start asking questions.');
            return;
        }

        try {
            setLoadingAsk(true);
            setAskError('');

            const data = await askResearchSession(trimmed, activeSessionId);

            // Clear input on success
            setQuestionText('');

            const userMsg = {
                id: `user-${Date.now()}`,
                role: 'USER',
                content: trimmed,
                created_at: new Date().toISOString()
            };

            const assistantMsg = {
                id: `assistant-${Date.now()}`,
                role: 'ASSISTANT',
                content: data.answer,
                created_at: new Date().toISOString(),
                evidence: (data.sources || []).map((src, idx) => ({
                    id: src.chunk_id || `ev-${Date.now()}-${idx}`,
                    paper_id: src.paper_id,
                    paper_title: src.paper_title || 'Paper',
                    chunk_id: src.chunk_id,
                    page_number: src.page_number,
                    text: src.text,
                    citation_id: src.citation_id
                }))
            };

            // Auto-title session if it has default generic title and this is the first message
            const isDefaultTitle = activeSession?.title === 'Research Session' || activeSession?.title === 'New Research Session';
            const isFirstMessage = (!activeSession?.messages || activeSession.messages.length === 0);
            let nextTitle = activeSession?.title || 'Research Session';
            if (isDefaultTitle && isFirstMessage) {
                const autoTitle = generateAutoTitle(trimmed);
                if (autoTitle && autoTitle !== nextTitle) {
                    nextTitle = autoTitle;
                    api.patch(`/ai/sessions/${activeSessionId}/`, { title: autoTitle }).catch((err) => {
                        console.warn('Failed to auto-update session title:', err);
                    });
                }
            }

            setActiveSession((prev) => ({
                ...prev,
                title: nextTitle,
                messages: [...(prev?.messages || []), userMsg, assistantMsg],
                updated_at: new Date().toISOString()
            }));

            setSessions((prev) =>
                prev.map((s) => (s.id === activeSessionId ? { ...s, title: nextTitle, updated_at: new Date().toISOString() } : s))
            );

            scrollToBottom();
        } catch (err) {
            if (err.response?.status === 400) {
                setAskError(err.response.data?.error || 'Bad request. Please check your question.');
            } else if (err.response?.status === 401) {
                setAskError('Authentication required.');
            } else if (err.response?.status === 403) {
                setAskError(err.response.data?.error || 'You do not have permission to ask questions in this session.');
            } else if (err.response?.status === 404) {
                setAskError('Research session not found.');
            } else if (err.response?.status === 429) {
                setAskError('Gemini API rate limit exceeded. Please wait a moment and try again.');
            } else if (err.response?.status === 503) {
                setAskError('Gemini is temporarily unavailable. Please try again shortly.');
            } else {
                setAskError(err.response?.data?.error || 'Network or server error. Please try again.');
            }
        } finally {
            setLoadingAsk(false);
        }
    };

    // Keyboard shortcut for Composer: Enter sends, Shift+Enter for newline
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendQuestion();
        }
    };

    // Render a single message (User or Assistant, with rich historical cards preserved)
    const renderMessage = (msg) => {
        const isUser = msg.role === 'USER';

        if (isUser) {
            return (
                <div key={msg.id} className="message-row user">
                    <div className="message-label">You</div>
                    <div className="message-card user">
                        <p className="message-text">{msg.content}</p>
                    </div>
                </div>
            );
        }

        // Assistant Message: Check for structured comparison, gap, thematic, or trend analysis JSON from past sessions
        const parsedComp = parseStructuredComparison(msg.content, activeSession?.papers || []);
        const parsedGap = !parsedComp ? parseStructuredGapAnalysis(msg.content, activeSession?.papers || []) : null;
        const parsedThematic = (!parsedComp && !parsedGap) ? parseStructuredThematicAnalysis(msg.content, activeSession?.papers || []) : null;
        const parsedTrend = (!parsedComp && !parsedGap && !parsedThematic) ? parseStructuredTrendAnalysis(msg.content, activeSession?.papers || []) : null;

        return (
            <div key={msg.id} className="message-row assistant">
                <div className="message-label">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                    </svg>
                    NForge
                </div>
                <div className="message-card assistant">
                    {parsedComp ? (
                        <div className="structured-comparison-view">
                            <span className="comparison-badge-tag">
                                Cross-Paper Synthesis Matrix
                            </span>

                            {parsedComp.overall_synthesis && (
                                <div className="comparison-box">
                                    <h4 className="comparison-box-title" style={{ color: 'var(--accent-primary)' }}>
                                        Overall Synthesis
                                    </h4>
                                    <MarkdownRenderer content={parsedComp.overall_synthesis} />
                                </div>
                            )}

                            {Array.isArray(parsedComp.similarities) && parsedComp.similarities.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Similarities
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedComp.similarities.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, fontWeight: 500 }}>{item.statement}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedComp.differences) && parsedComp.differences.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Differences
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedComp.differences.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, fontWeight: 500 }}>{item.statement}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedComp.methodology_comparison) && parsedComp.methodology_comparison.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Methodology Comparison
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedComp.methodology_comparison.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, lineHeight: 1.5 }}>{item.summary || item.statement}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedComp.findings_comparison) && parsedComp.findings_comparison.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Findings Comparison
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedComp.findings_comparison.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, lineHeight: 1.5 }}>{item.summary || item.statement}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedComp.research_gaps) && parsedComp.research_gaps.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Research Gaps & Limitations
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedComp.research_gaps.map((item, idx) => {
                                            const isExplicit = item.type === 'explicit';
                                            return (
                                                <div key={idx} className="comparison-box">
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', marginBottom: '0.5rem' }}>
                                                        <p style={{ margin: 0, fontWeight: 500 }}>{item.statement}</p>
                                                        <span
                                                            style={{
                                                                fontSize: '0.72rem',
                                                                fontWeight: 700,
                                                                textTransform: 'uppercase',
                                                                padding: '0.15rem 0.5rem',
                                                                borderRadius: 'var(--radius-full)',
                                                                background: isExplicit ? 'rgba(37, 99, 235, 0.12)' : 'rgba(245, 158, 11, 0.15)',
                                                                color: isExplicit ? 'var(--accent-primary)' : 'var(--warning)',
                                                                border: isExplicit ? '1px solid var(--accent-primary)' : '1px solid var(--warning)',
                                                            }}
                                                        >
                                                            {isExplicit ? 'Explicit Gap' : 'Potential Gap'}
                                                        </span>
                                                    </div>
                                                    {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                        <div style={{ marginTop: '0.5rem' }}>
                                                            {item.sources.map((src, sIdx) => (
                                                                <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : parsedGap ? (
                        <div className="structured-gap-view">
                            <span className="gap-badge-tag">
                                Multi-Paper Research Gap Analysis
                            </span>

                            {parsedGap.overall_assessment && (
                                <div className="comparison-box gap-assessment-box">
                                    <h4 className="comparison-box-title" style={{ color: 'var(--accent-primary)' }}>
                                        Overall Assessment
                                    </h4>
                                    <MarkdownRenderer content={parsedGap.overall_assessment} />
                                </div>
                            )}

                            {Array.isArray(parsedGap.common_limitations) && parsedGap.common_limitations.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Common Limitations
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedGap.common_limitations.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, fontWeight: 500 }}>{item.statement || item.summary}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedGap.methodological_gaps) && parsedGap.methodological_gaps.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Methodological Gaps
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedGap.methodological_gaps.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, fontWeight: 500 }}>{item.statement || item.summary}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedGap.dataset_population_gaps) && parsedGap.dataset_population_gaps.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Dataset & Population Gaps
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedGap.dataset_population_gaps.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, fontWeight: 500 }}>{item.statement || item.summary}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedGap.understudied_areas) && parsedGap.understudied_areas.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Understudied Areas
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedGap.understudied_areas.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, fontWeight: 500 }}>{item.statement || item.summary}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedGap.contradictions_inconsistencies) && parsedGap.contradictions_inconsistencies.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Contradictions & Inconsistencies
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedGap.contradictions_inconsistencies.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, fontWeight: 500 }}>{item.statement || item.summary}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedGap.unanswered_research_questions) && parsedGap.unanswered_research_questions.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Unanswered Research Questions
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedGap.unanswered_research_questions.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, fontWeight: 500 }}>{item.question || item.statement || item.summary}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedGap.future_research_directions) && parsedGap.future_research_directions.length > 0 && (
                                <div>
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Future Research Directions
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                        {parsedGap.future_research_directions.map((item, idx) => (
                                            <div key={idx} className="comparison-box">
                                                <p style={{ margin: 0, fontWeight: 500 }}>{item.direction || item.statement || item.summary}</p>
                                                {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                    <div style={{ marginTop: '0.5rem' }}>
                                                        {item.sources.map((src, sIdx) => (
                                                            <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : parsedThematic ? (
                        <div className="structured-thematic-view">
                            <span className="thematic-badge-tag">
                                Cross-Paper Thematic Analysis
                            </span>

                            {parsedThematic.overall_synthesis && (
                                <div className="comparison-box thematic-synthesis-box">
                                    <h4 className="comparison-box-title" style={{ color: 'var(--accent-primary)' }}>
                                        Overall Synthesis
                                    </h4>
                                    <MarkdownRenderer content={parsedThematic.overall_synthesis} />
                                </div>
                            )}

                            {Array.isArray(parsedThematic.themes) && parsedThematic.themes.length > 0 && (
                                <div className="thematic-themes-list">
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Identified Themes ({parsedThematic.themes.length})
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                        {parsedThematic.themes.map((themeItem, tIdx) => (
                                            <div key={tIdx} className="comparison-box thematic-theme-card">
                                                <div className="thematic-theme-header">
                                                    <span className="thematic-theme-number">Theme {tIdx + 1}</span>
                                                    <h5 className="thematic-theme-title">{themeItem.theme}</h5>
                                                </div>

                                                {themeItem.description && (
                                                    <p className="thematic-theme-desc">{themeItem.description}</p>
                                                )}

                                                {Array.isArray(themeItem.papers) && themeItem.papers.length > 0 && (
                                                    <div className="thematic-papers-section">
                                                        <h6 className="thematic-subheading">Papers Discussing this Theme</h6>
                                                        <div className="thematic-papers-list">
                                                            {themeItem.papers.map((paperEntry, pIdx) => (
                                                                <div key={pIdx} className="thematic-paper-entry">
                                                                    <div className="thematic-paper-entry-header">
                                                                        <span className="thematic-paper-entry-title">
                                                                            {paperEntry.paper_title || `Paper #${paperEntry.paper_id}`}
                                                                        </span>
                                                                    </div>
                                                                    {paperEntry.discussion && (
                                                                        <p className="thematic-paper-discussion">
                                                                            {paperEntry.discussion}
                                                                        </p>
                                                                    )}
                                                                    {Array.isArray(paperEntry.sources) && paperEntry.sources.length > 0 && (
                                                                        <div style={{ marginTop: '0.4rem' }}>
                                                                            {paperEntry.sources.map((src, sIdx) => (
                                                                                <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {themeItem.cross_paper_observation && (
                                                    <div className="thematic-observation-box">
                                                        <div className="thematic-observation-label">
                                                            Cross-Paper Observation
                                                        </div>
                                                        <p className="thematic-observation-text">
                                                            {themeItem.cross_paper_observation}
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : parsedTrend ? (
                        <div className="structured-trend-view">
                            <span className="trend-badge-tag">
                                Cross-Paper Research Trend Analysis
                            </span>

                            {parsedTrend.overall_trend && (
                                <div className="comparison-box trend-overall-box">
                                    <h4 className="comparison-box-title" style={{ color: 'var(--accent-primary)' }}>
                                        Overall Trend Analysis
                                    </h4>
                                    <MarkdownRenderer content={parsedTrend.overall_trend} />
                                </div>
                            )}

                            {Array.isArray(parsedTrend.research_evolution) && parsedTrend.research_evolution.length > 0 && (
                                <div className="trend-evolution-section">
                                    <h4 style={{ fontSize: '1rem', marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                                        Research Evolution
                                    </h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                        {parsedTrend.research_evolution.map((evItem, evIdx) => (
                                            <div key={evIdx} className="comparison-box trend-card">
                                                <div className="trend-header">
                                                    <span className="trend-number">Phase {evIdx + 1}</span>
                                                    <h5 className="trend-title">{evItem.phase || evItem.trend_title || `Evolution Step ${evIdx + 1}`}</h5>
                                                </div>

                                                {evItem.description && (
                                                    <p className="trend-desc">{evItem.description}</p>
                                                )}

                                                {Array.isArray(evItem.papers) && evItem.papers.length > 0 && (
                                                    <div className="trend-papers-section">
                                                        <h6 className="trend-subheading">Papers Representing this Evolution</h6>
                                                        <div className="trend-papers-list">
                                                            {evItem.papers.map((paperEntry, pIdx) => (
                                                                <div key={pIdx} className="trend-paper-entry">
                                                                    <div className="trend-paper-entry-header">
                                                                        <span className="trend-paper-entry-title">
                                                                            {paperEntry.paper_title || `Paper #${paperEntry.paper_id}`}
                                                                        </span>
                                                                    </div>
                                                                    {paperEntry.observation && (
                                                                        <p className="trend-paper-observation">
                                                                            {paperEntry.observation}
                                                                        </p>
                                                                    )}
                                                                    {Array.isArray(paperEntry.sources) && paperEntry.sources.length > 0 && (
                                                                        <div style={{ marginTop: '0.4rem' }}>
                                                                            {paperEntry.sources.map((src, sIdx) => (
                                                                                <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {evItem.cross_paper_observation && (
                                                    <div className="trend-observation-box">
                                                        <div className="trend-observation-label">
                                                            Cross-Paper Evolutionary Observation
                                                        </div>
                                                        <p className="trend-observation-text">
                                                            {evItem.cross_paper_observation}
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {Array.isArray(parsedTrend.emerging_directions) && parsedTrend.emerging_directions.length > 0 && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                    <h4 style={{ fontSize: '1rem', color: 'var(--text-primary)', margin: '0.25rem 0 0' }}>
                                        Emerging Research Directions
                                    </h4>
                                    {parsedTrend.emerging_directions.map((item, idx) => (
                                        <div key={idx} className="comparison-box trend-feature-box">
                                            <p className="trend-feature-title">{item.direction || item.summary || item.statement}</p>
                                            {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                <div style={{ marginTop: '0.5rem' }}>
                                                    {item.sources.map((src, sIdx) => (
                                                        <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}

                            {Array.isArray(parsedTrend.methodology_evolution) && parsedTrend.methodology_evolution.length > 0 && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                    <h4 style={{ fontSize: '1rem', color: 'var(--text-primary)', margin: '0.25rem 0 0' }}>
                                        Methodological Evolution
                                    </h4>
                                    {parsedTrend.methodology_evolution.map((item, idx) => (
                                        <div key={idx} className="comparison-box trend-feature-box">
                                            <p className="trend-feature-title">{item.trend || item.summary || item.statement}</p>
                                            {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                <div style={{ marginTop: '0.5rem' }}>
                                                    {item.sources.map((src, sIdx) => (
                                                        <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}

                            {Array.isArray(parsedTrend.future_directions) && parsedTrend.future_directions.length > 0 && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                    <h4 style={{ fontSize: '1rem', color: 'var(--text-primary)', margin: '0.25rem 0 0' }}>
                                        Future Research Trajectories
                                    </h4>
                                    {parsedTrend.future_directions.map((item, idx) => (
                                        <div key={idx} className="comparison-box trend-feature-box">
                                            <p className="trend-feature-title">{item.direction || item.summary || item.statement}</p>
                                            {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                <div style={{ marginTop: '0.5rem' }}>
                                                    {item.sources.map((src, sIdx) => (
                                                        <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="message-markdown-wrap">
                            <MarkdownRenderer content={msg.content} />
                        </div>
                    )}

                    {Array.isArray(msg.evidence) && msg.evidence.length > 0 && !parsedComp && !parsedGap && !parsedThematic && !parsedTrend && (
                        <div className="message-evidence-container">
                            <div className="evidence-header-label">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                    <polyline points="14 2 14 8 20 8"></polyline>
                                </svg>
                                Grounded Evidence Sources ({msg.evidence.length})
                            </div>
                            {msg.evidence.map((evItem) => (
                                <EvidenceSource key={evItem.id} source={evItem} projectId={projectId} />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="research-workspace">
            {/* Top Bar / Breadcrumb */}
            <header className="workspace-top-bar">
                <Link to={`/projects/${projectId}`} className="workspace-back-link">
                    &larr; Back to {project ? project.title : 'Project'}
                </Link>

                <div className="workspace-top-bar-right">
                    <button
                        className="mobile-sidebar-toggle-btn"
                        onClick={() => setIsMobileSidebarOpen((prev) => !prev)}
                        aria-label="Toggle sessions history"
                        type="button"
                    >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                        <span>Sessions ({sessions.length})</span>
                    </button>

                    <div className="workspace-project-pill">
                        <span className="project-pill-dot"></span>
                        <span>Research Workspace</span>
                    </div>
                </div>
            </header>

            {isMobileSidebarOpen && (
                <div 
                    className="mobile-sidebar-backdrop" 
                    onClick={() => setIsMobileSidebarOpen(false)}
                    aria-hidden="true"
                />
            )}

            {actionError && (
                <div className="alert-box error" style={{ marginBottom: '0.75rem', flexShrink: 0 }}>
                    {actionError}
                </div>
            )}

            {/* 2-Column Responsive Workspace Grid */}
            <div className="workspace-grid">
                {/* Left Column: Sessions History Sidebar */}
                <aside className={`workspace-sidebar ${isMobileSidebarOpen ? 'mobile-open' : ''}`}>
                    <div className="sidebar-header">
                        <div className="sidebar-title-row">
                            <h3 className="sidebar-heading">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <polyline points="12 6 12 12 16 14"></polyline>
                                </svg>
                                Research History
                            </h3>
                            <span className="sidebar-count-badge">
                                {sessions.length}
                            </span>
                        </div>

                        {!isViewer && (
                            <button
                                className="create-session-btn"
                                onClick={handleCreateSession}
                                disabled={creatingSession}
                                type="button"
                            >
                                <span style={{ fontSize: '1rem', lineHeight: 1 }}>+</span>
                                {creatingSession ? 'Creating...' : 'New Research Session'}
                            </button>
                        )}
                    </div>

                    {listError ? (
                        <div style={{ padding: '1.25rem', color: 'var(--danger)', fontSize: '0.85rem' }}>
                            {listError}
                        </div>
                    ) : loadingList ? (
                        <div className="loading-indicator">
                            <span className="spinner-icon"></span>
                            Loading history...
                        </div>
                    ) : sessions.length === 0 ? (
                        <div style={{ padding: '2rem 1.25rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                            <p style={{ margin: 0, fontSize: '0.85rem' }}>No sessions yet</p>
                        </div>
                    ) : (
                        <div className="sessions-scroll-list">
                            {sessions.map((session) => {
                                const isActive = session.id === activeSessionId;
                                const isRenamingThis = renamingSessionId === session.id;

                                return (
                                    <div
                                        key={session.id}
                                        className={`session-card ${isActive ? 'active' : ''}`}
                                        onClick={() => handleSelectSession(session.id)}
                                    >
                                        <div className="session-card-top">
                                            {isRenamingThis ? (
                                                <form
                                                    className="session-rename-input-wrap"
                                                    onSubmit={(e) => handleSaveRename(session.id, e)}
                                                    onClick={(e) => e.stopPropagation()}
                                                >
                                                    <input
                                                        type="text"
                                                        className="session-rename-input"
                                                        value={renameTitle}
                                                        onChange={(e) => {
                                                            setRenameTitle(e.target.value);
                                                            setRenameError('');
                                                        }}
                                                        onKeyDown={(e) => {
                                                            if (e.key === 'Escape') cancelRename();
                                                        }}
                                                        autoFocus
                                                    />
                                                    <button
                                                        type="submit"
                                                        className="action-btn-secondary"
                                                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                                                        disabled={isRenaming || !renameTitle.trim()}
                                                    >
                                                        Save
                                                    </button>
                                                    <button
                                                        type="button"
                                                        className="action-btn-secondary"
                                                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            cancelRename();
                                                        }}
                                                    >
                                                        &times;
                                                    </button>
                                                </form>
                                            ) : (
                                                <h4 className="session-title">{session.title}</h4>
                                            )}

                                            {!isViewer && (
                                                <div style={{ position: 'relative' }}>
                                                    <button
                                                        className="session-menu-trigger"
                                                        title="Options"
                                                        type="button"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            setOpenMenuId(openMenuId === session.id ? null : session.id);
                                                        }}
                                                    >
                                                        &#8943;
                                                    </button>

                                                    {openMenuId === session.id && (
                                                        <div
                                                            className="session-dropdown-menu"
                                                            onClick={(e) => e.stopPropagation()}
                                                        >
                                                            <button
                                                                className="dropdown-item"
                                                                onClick={(e) => startRename(session, e)}
                                                                type="button"
                                                            >
                                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                    <path d="M12 20h9"></path>
                                                                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                                                                </svg>
                                                                Rename
                                                            </button>
                                                            <button
                                                                className="dropdown-item delete"
                                                                onClick={(e) => openDeleteModal(session, e)}
                                                                type="button"
                                                            >
                                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                    <polyline points="3 6 5 6 21 6"></polyline>
                                                                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
                                                                </svg>
                                                                Delete
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>

                                        <div className="session-card-meta">
                                            <span className="session-card-date">{formatSessionTime(session.updated_at)}</span>
                                            <span className="session-card-papers-count">
                                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                                    <polyline points="14 2 14 8 20 8"></polyline>
                                                </svg>
                                                {session.papers && session.papers.length > 0
                                                    ? `${session.papers.length} ${session.papers.length === 1 ? 'paper' : 'papers'}`
                                                    : '0 papers'}
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </aside>

                {/* Right Column: Active Session Workspace (Clean, spacious 3-row layout) */}
                <main className="workspace-main">
                    {sessionError ? (
                        <div className="workspace-empty-state">
                            <div className="alert-box error">{sessionError}</div>
                        </div>
                    ) : loadingSession ? (
                        <div className="loading-indicator" style={{ height: '100%', minHeight: '300px' }}>
                            <span className="spinner-icon"></span>
                            Reconstructing saved research conversation...
                        </div>
                    ) : sessions.length === 0 ? (
                        /* Empty State: No sessions created yet */
                        <div className="workspace-empty-state">
                            <div className="empty-icon-bubble">
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                                </svg>
                            </div>
                            <h3 className="empty-state-title">No research sessions yet</h3>
                            <p className="empty-state-desc">
                                {isViewer
                                    ? 'No research sessions have been created for this project yet. Sessions created by collaborators will appear here.'
                                    : 'Create a session to start your research conversation and synthesize literature across papers.'}
                            </p>
                            {!isViewer && (
                                <button
                                    className="create-session-btn"
                                    style={{ width: 'auto', padding: '0.65rem 1.4rem' }}
                                    onClick={handleCreateSession}
                                    disabled={creatingSession}
                                    type="button"
                                >
                                    <span style={{ fontSize: '1rem', lineHeight: 1 }}>+</span>
                                    {creatingSession ? 'Creating...' : 'New Research Session'}
                                </button>
                            )}
                        </div>
                    ) : !activeSession ? (
                        /* Empty State: Sessions exist but none selected */
                        <div className="workspace-empty-state">
                            <div className="empty-icon-bubble">
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <path d="M12 8v4l3 3"></path>
                                </svg>
                            </div>
                            <h3 className="empty-state-title">Select a research session</h3>
                            <p className="empty-state-desc">
                                Choose a past session from the history sidebar or create a new one to continue literature review.
                            </p>
                        </div>
                    ) : (
                        /* Active Conversation Thread View */
                        <>
                            {/* Row 1: Compact Workspace Header & Attached Papers Bar */}
                            <div className="workspace-header-group">
                                <div className="workspace-active-header">
                                    <div className="active-session-title-wrap">
                                        {renamingSessionId === activeSession.id ? (
                                            <form
                                                className="active-title-rename-form"
                                                onSubmit={(e) => handleSaveRename(activeSession.id, e)}
                                            >
                                                <input
                                                    type="text"
                                                    className="active-title-rename-input"
                                                    value={renameTitle}
                                                    onChange={(e) => {
                                                        setRenameTitle(e.target.value);
                                                        setRenameError('');
                                                    }}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Escape') cancelRename();
                                                    }}
                                                    autoFocus
                                                    disabled={isRenaming}
                                                    maxLength={100}
                                                    placeholder="Enter session title..."
                                                />
                                                <button
                                                    type="submit"
                                                    className="action-btn-primary"
                                                    disabled={isRenaming || !renameTitle.trim()}
                                                >
                                                    {isRenaming ? 'Saving...' : 'Save'}
                                                </button>
                                                <button
                                                    type="button"
                                                    className="action-btn-secondary"
                                                    onClick={cancelRename}
                                                    disabled={isRenaming}
                                                >
                                                    Cancel
                                                </button>
                                                {renameError && <span className="rename-error-text">{renameError}</span>}
                                            </form>
                                        ) : (
                                            <div>
                                                <h2
                                                    className={`active-session-title ${!isViewer ? 'clickable' : ''}`}
                                                    onClick={!isViewer ? (e) => startRename(activeSession, e) : undefined}
                                                    title={!isViewer ? 'Click to rename session' : activeSession.title}
                                                >
                                                    <span>{activeSession.title}</span>
                                                    {!isViewer && (
                                                        <span className="title-edit-hint" aria-label="Edit title">
                                                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                <path d="M12 20h9"></path>
                                                                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                                                            </svg>
                                                        </span>
                                                    )}
                                                </h2>
                                                <div className="active-session-meta">
                                                    <span>{formatSessionTime(activeSession.updated_at)}</span>
                                                    {activeSession.papers && activeSession.papers.length > 0 && (
                                                        <span>
                                                            {' '} &middot; {activeSession.papers.length} {activeSession.papers.length === 1 ? 'paper' : 'papers'} attached
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {!isViewer && (
                                        <div className="active-session-actions">
                                            {renamingSessionId !== activeSession.id && (
                                                <button
                                                    className="action-btn-secondary"
                                                    onClick={(e) => startRename(activeSession, e)}
                                                    type="button"
                                                >
                                                    Rename
                                                </button>
                                            )}
                                            <button
                                                className="action-btn-danger"
                                                onClick={(e) => openDeleteModal(activeSession, e)}
                                                type="button"
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    )}
                                </div>

                                {/* Read-Only Viewer Banner */}
                                {isViewer && (
                                    <div className="workspace-viewer-banner">
                                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                            <circle cx="12" cy="12" r="10"></circle>
                                            <line x1="12" y1="16" x2="12" y2="12"></line>
                                            <line x1="12" y1="8" x2="12.01" y2="8"></line>
                                        </svg>
                                        <span>Read-only access &mdash; you can view this research session but cannot ask questions or modify analyses.</span>
                                    </div>
                                )}

                                {/* Compact Attached Papers Bar */}
                                <div className="workspace-papers-bar">
                                    <div className="papers-bar-left">
                                        <div className="papers-bar-title-wrap">
                                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                                <polyline points="14 2 14 8 20 8"></polyline>
                                            </svg>
                                            <span className="papers-bar-title">Attached Papers</span>
                                            <span className="papers-count-badge">
                                                {activeSession.papers?.length || 0}
                                            </span>
                                        </div>
                                        {!isViewer && (
                                            <button
                                                type="button"
                                                className="add-papers-btn"
                                                onClick={openAddPapersModal}
                                            >
                                                + Manage Papers
                                            </button>
                                        )}
                                    </div>
                                    <div className="papers-tags-list">
                                        {activeSession.papers && activeSession.papers.length > 0 ? (
                                            activeSession.papers.map((p) => (
                                                <span key={p.id} className="paper-tag-pill" title={p.title}>
                                                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, opacity: 0.65 }}>
                                                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                                        <polyline points="14 2 14 8 20 8"></polyline>
                                                    </svg>
                                                    <span className="paper-tag-title">{p.title}</span>
                                                    {!isViewer && (
                                                        <button
                                                            type="button"
                                                            className="paper-tag-remove"
                                                            onClick={() => handleRemovePaperFromSession(p.id)}
                                                            disabled={removingPaperId === p.id}
                                                            title="Remove paper from session"
                                                        >
                                                            {removingPaperId === p.id ? '...' : '\u00D7'}
                                                        </button>
                                                    )}
                                                </span>
                                            ))
                                        ) : (
                                            <span className="no-papers-hint">
                                                No papers attached to this session. Click + Manage Papers to attach papers.
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Row 2: Conversation Scroll Area (Dominant Region: 70–80%+ vertical space) */}
                            <div
                                className="conversation-scroll-area"
                                ref={chatScrollRef}
                                onScroll={handleConversationScroll}
                            >
                                {activeSession.messages && activeSession.messages.length > 0 ? (
                                    activeSession.messages.map(renderMessage)
                                ) : (
                                    <div className="empty-session-box">
                                        <div className="empty-session-icon">
                                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                                            </svg>
                                        </div>
                                        <h3 className="empty-session-title">Start your research</h3>
                                        <p className="empty-session-desc">
                                            Ask research questions across your attached papers to synthesize findings, evaluate methods, and uncover insights.
                                        </p>
                                        <div className="empty-session-hint">
                                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <circle cx="12" cy="12" r="10"></circle>
                                                <line x1="12" y1="16" x2="12" y2="12"></line>
                                                <line x1="12" y1="8" x2="12.01" y2="8"></line>
                                            </svg>
                                            <span>
                                                {(activeSession.papers?.length || 0) === 0
                                                    ? 'Attach papers using the Attached Papers bar above to get started.'
                                                    : `${activeSession.papers.length} ${activeSession.papers.length === 1 ? 'paper is' : 'papers are'} attached to this session. Type your question below to begin.`}
                                            </span>
                                        </div>
                                    </div>
                                )}

                                {loadingAsk && (
                                    <div className="message-row assistant">
                                        <div className="message-label">
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                                            </svg>
                                            NForge
                                        </div>
                                        <div className="ai-analyzing-banner">
                                            <span className="spinner-icon-sm"></span>
                                            <span>NForge AI is synthesizing research across session papers...</span>
                                        </div>
                                    </div>
                                )}

                                <div ref={messagesEndRef} />
                            </div>

                            {/* Row 3: Spacious Bottom Composer */}
                            <div className="workspace-composer">
                                {/* Floating Scroll to Latest Pill */}
                                {!isNearBottom && (activeSession.messages?.length || 0) > 0 && (
                                    <button
                                        type="button"
                                        className="scroll-to-bottom-pill"
                                        onClick={() => scrollToBottom(true)}
                                        aria-label="Scroll to latest message"
                                    >
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                            <line x1="12" y1="5" x2="12" y2="19"></line>
                                            <polyline points="19 12 12 19 5 12"></polyline>
                                        </svg>
                                        <span>Latest</span>
                                    </button>
                                )}

                                <div className="composer-container">
                                    {/* Research prompt shortcuts */}
                                    {activeSession.papers && activeSession.papers.length > 0 && (
                                        <div className="composer-shortcuts-row">
                                            <span className="composer-shortcuts-label">
                                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                                                </svg>
                                                Prompts:
                                            </span>
                                            <div className="composer-shortcuts-chips">
                                                {SESSION_RESEARCH_SHORTCUTS.map((item, idx) => (
                                                    <button
                                                        key={idx}
                                                        type="button"
                                                        className="composer-shortcut-chip"
                                                        disabled={isViewer || loadingAsk || !activeSession.papers?.length}
                                                        onClick={() => setQuestionText(item.prompt)}
                                                        title={item.prompt}
                                                    >
                                                        {item.label}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {askError && (
                                        <div className="alert-box error" style={{ marginBottom: '0.65rem' }}>
                                            {askError}
                                        </div>
                                    )}

                                    {activeSession.papers && activeSession.papers.length > 0 ? (
                                        <div className="composer-card">
                                            <textarea
                                                ref={textareaRef}
                                                className="composer-textarea"
                                                placeholder={
                                                    isViewer
                                                        ? "Read-only access — asking questions is disabled for viewers."
                                                        : "Ask a research question across session papers... (Enter to send, Shift+Enter for new line)"
                                                }
                                                value={questionText}
                                                onChange={(e) => setQuestionText(e.target.value)}
                                                onKeyDown={handleKeyDown}
                                                disabled={isViewer || loadingAsk}
                                                rows={2}
                                            />
                                            <div className="composer-bottom-bar">
                                                <div className="composer-key-hint">
                                                    <span><kbd>Enter</kbd> to send &bull; <kbd>Shift+Enter</kbd> for new line</span>
                                                </div>
                                                <button
                                                    className={`composer-send-btn ${isViewer ? 'read-only-btn' : ''}`}
                                                    onClick={handleSendQuestion}
                                                    disabled={isViewer || loadingAsk || !questionText.trim()}
                                                    title={isViewer ? "Read-only access" : "Send question (Enter)"}
                                                    type="button"
                                                >
                                                    {loadingAsk ? (
                                                        <>
                                                            <span className="spinner-icon-sm"></span>
                                                            <span>Synthesizing...</span>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <span>{isViewer ? "Read-only" : "Send"}</span>
                                                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                                                            </svg>
                                                        </>
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="composer-no-papers-card">
                                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <circle cx="12" cy="12" r="10"></circle>
                                                <line x1="12" y1="8" x2="12" y2="12"></line>
                                                <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                            </svg>
                                            <span>Add research papers to this session to ask questions.</span>
                                            {!isViewer && (
                                                <button
                                                    className="action-btn-primary"
                                                    onClick={openAddPapersModal}
                                                    type="button"
                                                >
                                                    + Manage Papers
                                                </button>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </>
                    )}
                </main>
            </div>

            {/* Add / Manage Papers Modal */}
            {isPapersModalOpen && (
                <div className="modal-overlay" onClick={() => setIsPapersModalOpen(false)}>
                    <div className="papers-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="papers-modal-header">
                            <h3 className="papers-modal-title">Manage Session Papers</h3>
                            <button
                                className="papers-modal-close"
                                onClick={() => setIsPapersModalOpen(false)}
                                type="button"
                            >
                                &times;
                            </button>
                        </div>
                        <div className="papers-modal-body">
                            <p className="papers-modal-desc">
                                Select which papers from <strong>{project?.title || 'this project'}</strong> belong to this research session:
                            </p>

                            {projectPapers.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-muted)' }}>
                                    <p style={{ margin: '0 0 1rem 0' }}>No papers uploaded to this project yet.</p>
                                    <Link
                                        to={`/projects/${projectId}`}
                                        className="action-btn-secondary"
                                        style={{ display: 'inline-block' }}
                                    >
                                        Go to Project to Upload Papers
                                    </Link>
                                </div>
                            ) : (
                                <div className="papers-modal-list">
                                    {projectPapers.map((paper) => {
                                        const isChecked = selectedModalPaperIds.includes(paper.id);
                                        return (
                                            <label
                                                key={paper.id}
                                                className={`papers-modal-item ${isChecked ? 'selected' : ''}`}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={isChecked}
                                                    onChange={() => togglePaperSelection(paper.id)}
                                                />
                                                <div className="papers-modal-item-info">
                                                    <span className="papers-modal-item-title">{paper.title}</span>
                                                    {paper.uploaded_at && (
                                                        <span className="papers-modal-item-date">
                                                            Uploaded {new Date(paper.uploaded_at).toLocaleDateString()}
                                                        </span>
                                                    )}
                                                </div>
                                            </label>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                        <div className="papers-modal-footer">
                            <button
                                type="button"
                                className="action-btn-secondary"
                                onClick={() => setIsPapersModalOpen(false)}
                                disabled={savingPapers}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="action-btn-primary"
                                onClick={handleSaveSessionPapers}
                                disabled={savingPapers || projectPapers.length === 0}
                            >
                                {savingPapers ? 'Saving...' : 'Save Papers'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Session Confirmation Modal */}
            {deletingSession && (
                <DeleteModal
                    isOpen={Boolean(deletingSession)}
                    title="Delete Research Session"
                    message={`Are you sure you want to delete "${deletingSession.title}"? All conversations and synthesis history in this session will be permanently deleted.`}
                    confirmLabel="Delete Session"
                    isLoading={isDeleting}
                    onConfirm={handleConfirmDelete}
                    onCancel={() => setDeletingSession(null)}
                />
            )}

            {/* Left-edge Fixed Notebook Dock Button */}
            <NotebookButton
                isOpen={isNotebookOpen}
                onClick={() => setIsNotebookOpen((prev) => !prev)}
                notesCount={notebookNotesCount}
            />

            {/* Paper-Specific Notebook Panel */}
            <PaperNotebookPanel
                isOpen={isNotebookOpen}
                onClose={() => setIsNotebookOpen(false)}
                papers={activeSession?.papers || []}
                onNotesCountChange={setNotebookNotesCount}
            />
        </div>
    );
}

export default ResearchWorkspace;
