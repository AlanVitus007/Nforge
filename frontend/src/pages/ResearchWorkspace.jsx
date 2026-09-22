import { useEffect, useState, useContext, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { AuthContext } from '../context/AuthContext';
import EvidenceSource from '../components/EvidenceSource';
import DeleteModal from '../components/DeleteModal';
import './ResearchWorkspace.css';

/**
 * Helper to safely parse and detect structured multi-paper comparison JSON.
 * Accepts both parsed object and JSON string, and enriches evidence paper titles.
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
        // Enrich paper titles on sources if paper mapping is available
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
 * Helper to generate a concise, safe auto-title from the user's first research question or comparison focus.
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
 * Research prompt shortcuts for Single-Paper analysis.
 */
const SINGLE_PAPER_SHORTCUTS = [
    {
        label: 'Summarize this paper',
        prompt: 'Summarize this paper and explain its main contribution.'
    },
    {
        label: 'Explain the methodology',
        prompt: 'Explain the methodology used in this paper, including the study design, data, methods, and evaluation approach.'
    },
    {
        label: 'Identify key findings',
        prompt: 'Identify the key findings and results reported in this paper.'
    },
    {
        label: 'Identify limitations',
        prompt: 'Identify the main limitations acknowledged or evident from this paper.'
    },
    {
        label: 'Find research gaps',
        prompt: 'Identify research gaps suggested by this paper.'
    },
    {
        label: 'Suggest future research directions',
        prompt: 'Suggest possible future research directions based on the gaps and limitations discussed in this paper.'
    }
];

/**
 * Helper to safely parse and detect structured multi-paper research gap analysis JSON.
 * Accepts both parsed object and JSON string, and enriches evidence paper titles.
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
        // Enrich paper titles on sources if paper mapping is available
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
 * Research prompt shortcuts for Multi-Paper comparison.
 */
const COMPARISON_SHORTCUTS = [
    {
        label: 'Compare methodology',
        prompt: 'Compare the methodology and study design used across these papers.'
    },
    {
        label: 'Compare key findings',
        prompt: 'Compare the key findings and results across these papers.'
    },
    {
        label: 'Compare limitations',
        prompt: 'Compare the limitations identified in these papers.'
    },
    {
        label: 'Compare research gaps',
        prompt: 'Compare the research gaps identified or implied by these papers.'
    },
    {
        label: 'Compare study design',
        prompt: 'Compare the study designs, datasets, and evaluation approaches used in these papers.'
    },
    {
        label: 'Give an overall comparison',
        prompt: 'Provide an overall comparison of the selected papers, including similarities, differences, methodology, findings, limitations, and research gaps.'
    }
];

/**
 * Research prompt shortcuts for Multi-Paper Research Gap Analysis.
 */
const RESEARCH_GAP_SHORTCUTS = [
    {
        label: 'Find research gaps',
        prompt: 'Identify the major research gaps across these papers.'
    },
    {
        label: 'Identify methodological gaps',
        prompt: 'Identify the methodological gaps and study limitations across these papers.'
    },
    {
        label: 'Find dataset/population gaps',
        prompt: 'Identify dataset, sample size, or population gaps across these papers.'
    },
    {
        label: 'Identify contradictions',
        prompt: 'Identify contradictions or inconsistent findings across these papers.'
    },
    {
        label: 'Find unanswered research questions',
        prompt: 'Identify unanswered research questions and unexplored areas across these papers.'
    },
    {
        label: 'Suggest future research directions',
        prompt: 'Suggest promising future research directions based on the collective gaps of these papers.'
    }
];

const DEFAULT_GAP_QUESTION = 'Identify the major research gaps, limitations, unanswered questions, and future research directions across these papers.';

function ResearchWorkspace() {
    const { projectId } = useParams();
    const navigate = useNavigate();
    const { user, loading: authLoading } = useContext(AuthContext);

    const [project, setProject] = useState(null);
    const [projectPapers, setProjectPapers] = useState([]);
    const [sessions, setSessions] = useState([]);
    const [activeSessionId, setActiveSessionId] = useState(null);
    const [activeSession, setActiveSession] = useState(null);

    // Papers Management Modal state
    const [isPapersModalOpen, setIsPapersModalOpen] = useState(false);
    const [selectedModalPaperIds, setSelectedModalPaperIds] = useState([]);
    const [savingPapers, setSavingPapers] = useState(false);
    const [removingPaperId, setRemovingPaperId] = useState(null);

    // Chat Mode: 'ask' (single-paper) or 'compare' (multi-paper)
    const [chatMode, setChatMode] = useState('ask');

    // Live Single-Paper Ask Question State
    const [selectedPaperId, setSelectedPaperId] = useState('');
    const [questionText, setQuestionText] = useState('');
    const [loadingAsk, setLoadingAsk] = useState(false);
    const [askError, setAskError] = useState('');

    // Live Multi-Paper Comparison State
    const [selectedComparisonPaperIds, setSelectedComparisonPaperIds] = useState([]);
    const [comparisonQuestion, setComparisonQuestion] = useState('');
    const [loadingCompare, setLoadingCompare] = useState(false);
    const [compareError, setCompareError] = useState('');

    // Live Multi-Paper Research Gap Analysis State
    const [selectedGapPaperIds, setSelectedGapPaperIds] = useState([]);
    const [gapQuestion, setGapQuestion] = useState('');
    const [loadingGap, setLoadingGap] = useState(false);
    const [gapError, setGapError] = useState('');

    // Loading & Action states
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

    const messagesEndRef = useRef(null);
    const currentSelectIdRef = useRef(null);

    // Redirect if unauthenticated
    useEffect(() => {
        if (!authLoading && !user) {
            navigate('/login');
        }
    }, [user, authLoading, navigate]);

    const scrollToBottom = () => {
        requestAnimationFrame(() => {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        });
    };

    // Select and open an existing session (0 Gemini calls) with race condition protection
    const handleSelectSession = useCallback(async (sessionId) => {
        currentSelectIdRef.current = sessionId;
        try {
            setActiveSessionId(sessionId);
            setActiveSession(null); // Clear previous session messages immediately so Session A does not linger
            setLoadingSession(true);
            setSessionError('');
            setAskError('');
            setQuestionText('');
            setCompareError('');
            setComparisonQuestion('');
            setGapError('');
            setGapQuestion('');
            setChatMode('ask');

            const res = await api.get(`/ai/sessions/${sessionId}/`);

            // Discard stale responses if user clicked another session while this request was in flight
            if (currentSelectIdRef.current !== sessionId) return;

            const sessionData = res.data;
            setActiveSession(sessionData);

            // Set selected paper to first paper in this session
            if (sessionData.papers && sessionData.papers.length > 0) {
                setSelectedPaperId(String(sessionData.papers[0].id));
                const compPaperIds = sessionData.papers.slice(0, 4).map((p) => p.id);
                setSelectedComparisonPaperIds(compPaperIds);
                setSelectedGapPaperIds(compPaperIds);
            } else {
                setSelectedPaperId('');
                setSelectedComparisonPaperIds([]);
                setSelectedGapPaperIds([]);
            }
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

                // 1. Fetch project meta for breadcrumb
                try {
                    const projRes = await api.get(`/projects/${projectId}/`);
                    setProject(projRes.data);
                } catch {
                    // Non-fatal
                }

                // 2. Fetch project papers for paper selection
                try {
                    const papersRes = await api.get(`/projects/${projectId}/papers/`);
                    setProjectPapers(papersRes.data || []);
                } catch {
                    // Non-fatal
                }

                // 3. Fetch research sessions
                const sessRes = await api.get(`/ai/sessions/?project_id=${projectId}`);
                const fetchedSessions = sessRes.data || [];
                setSessions(fetchedSessions);

                // If sessions exist, auto-open the most recently updated session
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
    }, [projectId, handleSelectSession]);

    // Close menu when clicking outside
    useEffect(() => {
        const handleGlobalClick = () => setOpenMenuId(null);
        window.addEventListener('click', handleGlobalClick);
        return () => window.removeEventListener('click', handleGlobalClick);
    }, []);

    // Create a new session (0 Gemini calls)
    const handleCreateSession = async () => {
        if (creatingSession) return;
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
            setSelectedPaperId('');
            setSelectedComparisonPaperIds([]);
            setSelectedGapPaperIds([]);
            setQuestionText('');
            setComparisonQuestion('');
            setGapQuestion('');
            setAskError('');
            setCompareError('');
            setGapError('');
            setChatMode('ask');
        } catch (err) {
            setActionError(err.response?.data?.error || 'Failed to create research session.');
        } finally {
            setCreatingSession(false);
        }
    };

    // Rename session
    const startRename = (session, e) => {
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
        if (e) e.stopPropagation();
        setDeletingSession(session);
        setOpenMenuId(null);
    };

    const handleConfirmDelete = async () => {
        if (!deletingSession || isDeleting) return;
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
        if (!activeSessionId) return;
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

            // If selectedPaperId is no longer in papers, update it
            const paperStillSelected = updated.papers?.some((p) => String(p.id) === selectedPaperId);
            if (!paperStillSelected) {
                setSelectedPaperId(updated.papers?.[0]?.id ? String(updated.papers[0].id) : '');
            }

            // Keep comparison selection in sync with updated papers
            setSelectedComparisonPaperIds((prev) => {
                const validIds = prev.filter((id) => selectedModalPaperIds.includes(id));
                if (validIds.length < 2 && selectedModalPaperIds.length >= 2) {
                    return selectedModalPaperIds.slice(0, 4);
                }
                return validIds.slice(0, 4);
            });

            // Keep gap selection in sync with updated papers
            setSelectedGapPaperIds((prev) => {
                const validIds = prev.filter((id) => selectedModalPaperIds.includes(id));
                if (validIds.length < 2 && selectedModalPaperIds.length >= 2) {
                    return selectedModalPaperIds.slice(0, 4);
                }
                return validIds.slice(0, 4);
            });

            // If papers fall below 2, revert chatMode to 'ask'
            if ((updated.papers?.length || 0) < 2) {
                if (chatMode === 'compare' || chatMode === 'gap') {
                    setChatMode('ask');
                }
            }

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
        if (removingPaperId || !activeSessionId || !activeSession?.papers) return;
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

            if (selectedPaperId === String(paperIdToRemove)) {
                setSelectedPaperId(updated.papers?.[0]?.id ? String(updated.papers[0].id) : '');
            }

            setSelectedComparisonPaperIds((prev) => prev.filter((id) => id !== paperIdToRemove));
            setSelectedGapPaperIds((prev) => prev.filter((id) => id !== paperIdToRemove));

            if ((updated.papers?.length || 0) < 2) {
                if (chatMode === 'compare' || chatMode === 'gap') {
                    setChatMode('ask');
                }
            }

            setSessions((prev) =>
                prev.map((s) => (s.id === activeSessionId ? { ...s, papers: updated.papers, updated_at: updated.updated_at } : s))
            );
        } catch (err) {
            setActionError(err.response?.data?.error || 'Failed to remove paper from session.');
        } finally {
            setRemovingPaperId(null);
        }
    };

    // Toggle Paper Selection for Multi-Paper Comparison (enforce min 2, max 4)
    const handleToggleComparisonPaper = (paperId) => {
        setSelectedComparisonPaperIds((prev) => {
            if (prev.includes(paperId)) {
                return prev.filter((id) => id !== paperId);
            }
            if (prev.length >= 4) {
                return prev; // Maximum 4 papers strictly enforced
            }
            return [...prev, paperId];
        });
    };

    // Toggle Paper Selection for Research Gap Analysis (enforce min 2, max 4)
    const handleToggleGapPaper = (paperId) => {
        setSelectedGapPaperIds((prev) => {
            if (prev.includes(paperId)) {
                return prev.filter((id) => id !== paperId);
            }
            if (prev.length >= 4) {
                return prev; // Maximum 4 papers strictly enforced
            }
            return [...prev, paperId];
        });
    };

    // Send Single-Paper Research Question via POST /api/ai/ask/
    const handleSendQuestion = async () => {
        if (loadingAsk || loadingCompare) return;
        const trimmed = questionText.trim();
        if (!trimmed) return;
        if (!selectedPaperId || !activeSessionId) return;

        const paperIdInt = parseInt(selectedPaperId, 10);
        if (isNaN(paperIdInt)) return;

        try {
            setLoadingAsk(true);
            setAskError('');

            const res = await api.post('/ai/ask/', {
                paper_id: paperIdInt,
                question: trimmed,
                session_id: activeSessionId
            });

            // Question sent successfully, clear the input
            setQuestionText('');

            // Resolve paper title from current session data
            const currentPaper = activeSession.papers?.find((p) => p.id === paperIdInt);
            const paperTitle = currentPaper ? currentPaper.title : 'Paper';

            const userMsg = {
                id: `user-${Date.now()}`,
                role: 'USER',
                content: trimmed,
                created_at: new Date().toISOString()
            };

            const assistantMsg = {
                id: `assistant-${Date.now()}`,
                role: 'ASSISTANT',
                content: res.data.answer,
                created_at: new Date().toISOString(),
                evidence: (res.data.sources || []).map((src, idx) => ({
                    id: src.chunk_id || `ev-${Date.now()}-${idx}`,
                    paper_id: paperIdInt,
                    paper_title: paperTitle,
                    chunk_id: src.chunk_id,
                    page_number: src.page_number,
                    text: src.text
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
                setAskError('You do not have access to this research session.');
            } else if (err.response?.status === 404) {
                setAskError('Research session or paper not found.');
            } else if (err.response?.status === 429) {
                setAskError('Gemini API rate limit exceeded. Please try again later.');
            } else if (err.response?.status === 503) {
                setAskError('Gemini is temporarily unavailable. Please try again shortly.');
            } else {
                setAskError(err.response?.data?.error || 'Network or server error. Please try again.');
            }
            // Keep questionText intact so user can retry manually
        } finally {
            setLoadingAsk(false);
        }
    };

    // Send Multi-Paper Comparison via POST /api/ai/compare/
    const handleGenerateComparison = async () => {
        if (loadingCompare || loadingAsk) return;

        if (selectedComparisonPaperIds.length < 2 || selectedComparisonPaperIds.length > 4) {
            setCompareError('Please select between 2 and 4 papers for comparison.');
            return;
        }

        if (!activeSessionId) return;

        const trimmed = comparisonQuestion.trim();
        const displayQuestion = trimmed || 'Cross-Paper Comparison Synthesis';

        try {
            setLoadingCompare(true);
            setCompareError('');

            const res = await api.post('/ai/compare/', {
                paper_ids: selectedComparisonPaperIds,
                question: trimmed,
                session_id: activeSessionId
            });

            // Comparison request succeeded, clear input
            setComparisonQuestion('');

            const comparisonData = res.data.comparison || {};

            const userMsg = {
                id: `user-${Date.now()}`,
                role: 'USER',
                content: displayQuestion,
                created_at: new Date().toISOString()
            };

            const assistantMsg = {
                id: `assistant-${Date.now()}`,
                role: 'ASSISTANT',
                content: comparisonData,
                created_at: new Date().toISOString()
            };

            // Auto-title session if it has default generic title and this is the first message
            const isDefaultTitle = activeSession?.title === 'Research Session' || activeSession?.title === 'New Research Session';
            const isFirstMessage = (!activeSession?.messages || activeSession.messages.length === 0);
            let nextCompTitle = activeSession?.title || 'Research Session';
            if (isDefaultTitle && isFirstMessage) {
                const autoTitle = generateAutoTitle(trimmed || 'Cross-Paper Comparison');
                if (autoTitle && autoTitle !== nextCompTitle) {
                    nextCompTitle = autoTitle;
                    api.patch(`/ai/sessions/${activeSessionId}/`, { title: autoTitle }).catch((err) => {
                        console.warn('Failed to auto-update session title:', err);
                    });
                }
            }

            setActiveSession((prev) => ({
                ...prev,
                title: nextCompTitle,
                messages: [...(prev?.messages || []), userMsg, assistantMsg],
                updated_at: new Date().toISOString()
            }));

            setSessions((prev) =>
                prev.map((s) => (s.id === activeSessionId ? { ...s, title: nextCompTitle, updated_at: new Date().toISOString() } : s))
            );

            scrollToBottom();
        } catch (err) {
            if (err.response?.status === 400) {
                setCompareError(err.response.data?.error || 'Please select between 2 and 4 papers.');
            } else if (err.response?.status === 401) {
                setCompareError('Authentication required.');
            } else if (err.response?.status === 403) {
                setCompareError('You do not have access to one or more selected papers or this session.');
            } else if (err.response?.status === 404) {
                setCompareError('Research session or papers not found.');
            } else if (err.response?.status === 429) {
                setCompareError('Gemini API rate limit exceeded. Please try again later.');
            } else if (err.response?.status === 503) {
                setCompareError('Gemini is temporarily unavailable. Please try again shortly.');
            } else {
                setCompareError(err.response?.data?.error || 'Network or server error. Please try again.');
            }
        } finally {
            setLoadingCompare(false);
        }
    };

    // Send Multi-Paper Research Gap Analysis via POST /api/ai/gap-analysis/
    const handleGenerateGapAnalysis = async () => {
        if (loadingGap || loadingCompare || loadingAsk) return;

        if (selectedGapPaperIds.length < 2 || selectedGapPaperIds.length > 4) {
            setGapError('Please select between 2 and 4 papers for research gap analysis.');
            return;
        }

        if (!activeSessionId) return;

        const trimmed = gapQuestion.trim();
        const effectiveQuestion = trimmed || DEFAULT_GAP_QUESTION;

        try {
            setLoadingGap(true);
            setGapError('');

            const res = await api.post('/ai/gap-analysis/', {
                paper_ids: selectedGapPaperIds,
                question: effectiveQuestion,
                session_id: activeSessionId
            });

            // Clear input
            setGapQuestion('');

            const gapData = res.data.gap_analysis || {};

            // Collect all unique sources from response across all categories
            const paperMap = {};
            (activeSession?.papers || []).forEach((p) => {
                paperMap[p.id] = p.title;
            });

            const allSources = [];
            const seenKeys = new Set();
            const sections = [
                gapData.common_limitations,
                gapData.methodological_gaps,
                gapData.dataset_population_gaps,
                gapData.understudied_areas,
                gapData.contradictions_inconsistencies,
                gapData.unanswered_research_questions,
                gapData.future_research_directions,
            ];

            sections.forEach((sec) => {
                if (Array.isArray(sec)) {
                    sec.forEach((item) => {
                        if (item && Array.isArray(item.sources)) {
                            item.sources.forEach((src) => {
                                if (src) {
                                    const key = src.chunk_id ? `${src.paper_id}-${src.chunk_id}` : `${src.paper_id}-${src.page_number}-${src.text}`;
                                    if (!seenKeys.has(key)) {
                                        seenKeys.add(key);
                                        allSources.push({
                                            id: src.chunk_id || `ev-gap-${Date.now()}-${allSources.length}`,
                                            paper_id: src.paper_id,
                                            paper_title: paperMap[src.paper_id] || src.paper_title || 'Paper',
                                            chunk_id: src.chunk_id,
                                            page_number: src.page_number,
                                            text: src.text || ''
                                        });
                                    }
                                }
                            });
                        }
                    });
                }
            });

            const userMsg = {
                id: `user-${Date.now()}`,
                role: 'USER',
                content: effectiveQuestion,
                created_at: new Date().toISOString()
            };

            const assistantMsg = {
                id: `assistant-${Date.now()}`,
                role: 'ASSISTANT',
                content: gapData,
                created_at: new Date().toISOString(),
                evidence: allSources
            };

            // Auto-title session if default title
            const isDefaultTitle = activeSession?.title === 'Research Session' || activeSession?.title === 'New Research Session';
            const isFirstMessage = (!activeSession?.messages || activeSession.messages.length === 0);
            let nextGapTitle = activeSession?.title || 'Research Session';
            if (isDefaultTitle && isFirstMessage) {
                const autoTitle = generateAutoTitle(effectiveQuestion);
                if (autoTitle && autoTitle !== nextGapTitle) {
                    nextGapTitle = autoTitle;
                    api.patch(`/ai/sessions/${activeSessionId}/`, { title: autoTitle }).catch((err) => {
                        console.warn('Failed to auto-update session title:', err);
                    });
                }
            }

            setActiveSession((prev) => ({
                ...prev,
                title: nextGapTitle,
                messages: [...(prev?.messages || []), userMsg, assistantMsg],
                updated_at: new Date().toISOString()
            }));

            setSessions((prev) =>
                prev.map((s) => (s.id === activeSessionId ? { ...s, title: nextGapTitle, updated_at: new Date().toISOString() } : s))
            );

            scrollToBottom();
        } catch (err) {
            if (err.response?.status === 400) {
                setGapError(err.response.data?.error || 'Please select between 2 and 4 papers.');
            } else if (err.response?.status === 401) {
                setGapError('Authentication required.');
            } else if (err.response?.status === 403) {
                setGapError('You do not have access to one or more selected papers or this session.');
            } else if (err.response?.status === 404) {
                setGapError('Research session or papers not found.');
            } else if (err.response?.status === 429) {
                setGapError('Gemini API rate limit exceeded. Please try again later.');
            } else if (err.response?.status === 503) {
                setGapError('Gemini is temporarily unavailable. Please try again shortly.');
            } else {
                setGapError(err.response?.data?.error || 'Network or server error. Please try again.');
            }
        } finally {
            setLoadingGap(false);
        }
    };

    // Keyboard shortcut for Single-Paper Ask
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendQuestion();
        }
    };

    // Render a single message (User or Assistant)
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

        // Assistant Message: Check for structured comparison or research gap analysis JSON
        const parsedComp = parseStructuredComparison(msg.content, activeSession?.papers || []);
        const parsedGap = !parsedComp ? parseStructuredGapAnalysis(msg.content, activeSession?.papers || []) : null;

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

                            {/* Overall Synthesis */}
                            {parsedComp.overall_synthesis && (
                                <div className="comparison-box">
                                    <h4 className="comparison-box-title" style={{ color: 'var(--accent-primary)' }}>
                                        Overall Synthesis
                                    </h4>
                                    <p style={{ margin: 0, lineHeight: 1.6, color: 'var(--text-primary)' }}>
                                        {parsedComp.overall_synthesis}
                                    </p>
                                </div>
                            )}

                            {/* Similarities */}
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

                            {/* Differences */}
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

                            {/* Methodology Comparison */}
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

                            {/* Findings Comparison */}
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

                            {/* Research Gaps & Limitations */}
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
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <line x1="12" y1="8" x2="12" y2="12"></line>
                                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                </svg>
                                Multi-Paper Research Gap Analysis
                            </span>

                            {/* Overall Assessment */}
                            {parsedGap.overall_assessment && (
                                <div className="comparison-box gap-assessment-box">
                                    <h4 className="comparison-box-title" style={{ color: 'var(--accent-primary)' }}>
                                        Overall Assessment
                                    </h4>
                                    <p style={{ margin: 0, lineHeight: 1.6, color: 'var(--text-primary)' }}>
                                        {parsedGap.overall_assessment}
                                    </p>
                                </div>
                            )}

                            {/* Common Limitations */}
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

                            {/* Methodological Gaps */}
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

                            {/* Dataset / Population Gaps */}
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

                            {/* Understudied Areas */}
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

                            {/* Contradictions & Inconsistencies */}
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

                            {/* Unanswered Research Questions */}
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

                            {/* Future Research Directions */}
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
                    ) : (
                        <p className="message-text">{msg.content}</p>
                    )}

                    {/* Saved Grounded Evidence Sources (Single-Paper Ask) */}
                    {Array.isArray(msg.evidence) && msg.evidence.length > 0 && !parsedComp && !parsedGap && (
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

    const hasAtLeastTwoPapers = (activeSession?.papers?.length || 0) >= 2;

    return (
        <div className="research-workspace">
            {/* Top Bar / Breadcrumb */}
            <header className="workspace-top-bar">
                <Link to={`/projects/${projectId}`} className="workspace-back-link">
                    &larr; Back to {project ? project.title : 'Project'}
                </Link>

                <div className="workspace-project-pill">
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-primary)' }}></span>
                    <span>Research Workspace</span>
                </div>
            </header>

            {actionError && (
                <div className="alert-box error" style={{ marginBottom: '1.25rem' }}>
                    {actionError}
                </div>
            )}

            {/* 2-Column Responsive Workspace Grid */}
            <div className="workspace-grid">
                {/* Left Column: Sessions History Sidebar */}
                <aside className="workspace-sidebar">
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

                        <button
                            className="create-session-btn"
                            onClick={handleCreateSession}
                            disabled={creatingSession}
                            type="button"
                        >
                            <span style={{ fontSize: '1rem', lineHeight: 1 }}>+</span>
                            {creatingSession ? 'Creating...' : 'New Research Session'}
                        </button>
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

                {/* Right Column: Active Session Conversation Thread */}
                <main className="workspace-main">
                    {sessionError ? (
                        <div className="workspace-empty-state">
                            <div className="alert-box error">{sessionError}</div>
                        </div>
                    ) : loadingSession ? (
                        <div className="loading-indicator" style={{ height: '100%', minHeight: '400px' }}>
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
                                Create a session to start your research conversation and view saved synthesis history.
                            </p>
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
                                                className="active-session-title clickable"
                                                onClick={(e) => startRename(activeSession, e)}
                                                title="Click to rename session"
                                            >
                                                <span>{activeSession.title}</span>
                                                <span className="title-edit-hint" aria-label="Edit title">
                                                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                        <path d="M12 20h9"></path>
                                                        <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                                                    </svg>
                                                </span>
                                            </h2>
                                            <div className="active-session-meta">
                                                <span>{formatSessionTime(activeSession.updated_at)}</span>
                                                {activeSession.papers && activeSession.papers.length > 0 && (
                                                    <span>
                                                        {' '} &middot; {activeSession.papers.length} {activeSession.papers.length === 1 ? 'paper' : 'papers'} in session
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>

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
                            </div>

                            {/* Research Papers Section */}
                            <div className="workspace-papers-bar">
                                <div className="papers-bar-left">
                                    <div className="papers-bar-title-wrap">
                                        <span className="papers-bar-title">
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                                <polyline points="14 2 14 8 20 8"></polyline>
                                            </svg>
                                            Research Papers
                                        </span>
                                        <span className="papers-count-badge">
                                            {activeSession.papers?.length || 0}
                                        </span>
                                    </div>
                                    <button
                                        type="button"
                                        className="add-papers-btn"
                                        onClick={openAddPapersModal}
                                    >
                                        + Add Papers
                                    </button>
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
                                                <button
                                                    type="button"
                                                    className="paper-tag-remove"
                                                    onClick={() => handleRemovePaperFromSession(p.id)}
                                                    disabled={removingPaperId === p.id}
                                                    title="Remove paper from session"
                                                >
                                                    {removingPaperId === p.id ? '...' : '\u00D7'}
                                                </button>
                                            </span>
                                        ))
                                    ) : (
                                        <span className="no-papers-hint">
                                            No papers in this session. Add papers to ask targeted research questions or compare studies.
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* Conversation Scrollable Thread */}
                            <div className="conversation-scroll-area">
                                {activeSession.messages && activeSession.messages.length > 0 ? (
                                    activeSession.messages.map(renderMessage)
                                ) : (
                                    <div className="empty-session-box">
                                        <div className="empty-session-icon">
                                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                                                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
                                            </svg>
                                        </div>
                                        <h3 className="empty-session-title">Start your research</h3>
                                        <p className="empty-session-desc">
                                            Ask a question about one of your papers, or compare multiple papers.
                                        </p>
                                        <div className="empty-session-hint">
                                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <circle cx="12" cy="12" r="10"></circle>
                                                <line x1="12" y1="16" x2="12" y2="12"></line>
                                                <line x1="12" y1="8" x2="12.01" y2="8"></line>
                                            </svg>
                                            <span>
                                                {(activeSession.papers?.length || 0) === 0
                                                    ? 'Attach papers using the Research Papers section above to get started.'
                                                    : `${activeSession.papers.length} ${activeSession.papers.length === 1 ? 'paper is' : 'papers are'} attached to this session. Choose a mode below to ask a question or compare.`}
                                            </span>
                                        </div>
                                    </div>
                                )}

                                {loadingAsk && (
                                    <div className="ai-analyzing-banner">
                                        <span className="spinner-icon-sm"></span>
                                        <span>NForge AI is analyzing the paper...</span>
                                    </div>
                                )}

                                {loadingCompare && (
                                    <div className="ai-analyzing-banner">
                                        <span className="spinner-icon-sm"></span>
                                        <span>NForge AI is synthesizing cross-paper comparison...</span>
                                    </div>
                                )}

                                {loadingGap && (
                                    <div className="ai-analyzing-banner">
                                        <span className="spinner-icon-sm"></span>
                                        <span>NForge AI is analyzing research gaps across papers...</span>
                                    </div>
                                )}

                                <div ref={messagesEndRef} />
                            </div>

                            {/* Chat Footer: Action Mode Tabs & Inputs */}
                            <div className="workspace-chat-footer">
                                {activeSession.papers && activeSession.papers.length > 0 ? (
                                    <>
                                        {/* Action Mode Toggle */}
                                        <div className="chat-mode-tabs">
                                            <button
                                                type="button"
                                                className={`chat-mode-tab ${chatMode === 'ask' ? 'active' : ''}`}
                                                onClick={() => setChatMode('ask')}
                                                disabled={loadingAsk || loadingCompare || loadingGap}
                                            >
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                                                </svg>
                                                Ask Single Paper
                                            </button>
                                            <button
                                                type="button"
                                                className={`chat-mode-tab ${chatMode === 'compare' ? 'active' : ''}`}
                                                onClick={() => setChatMode('compare')}
                                                disabled={loadingAsk || loadingCompare || loadingGap || !hasAtLeastTwoPapers}
                                                title={!hasAtLeastTwoPapers ? 'Add at least 2 papers to compare' : 'Compare 2 to 4 papers'}
                                            >
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                    <polyline points="16 3 21 3 21 8"></polyline>
                                                    <line x1="4" y1="20" x2="21" y2="3"></line>
                                                    <polyline points="21 16 21 21 16 21"></polyline>
                                                    <line x1="15" y1="15" x2="21" y2="21"></line>
                                                    <line x1="4" y1="4" x2="9" y2="9"></line>
                                                </svg>
                                                Compare Papers
                                                {!hasAtLeastTwoPapers ? (
                                                    <span className="mode-tab-badge disabled">Requires 2+ papers</span>
                                                ) : (
                                                    <span className="mode-tab-badge">2–4</span>
                                                )}
                                            </button>
                                            <button
                                                type="button"
                                                className={`chat-mode-tab ${chatMode === 'gap' ? 'active' : ''}`}
                                                onClick={() => setChatMode('gap')}
                                                disabled={loadingAsk || loadingCompare || loadingGap || !hasAtLeastTwoPapers}
                                                title={!hasAtLeastTwoPapers ? 'Add at least 2 papers to analyze gaps' : 'Identify research gaps across 2 to 4 papers'}
                                            >
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                    <circle cx="12" cy="12" r="10"></circle>
                                                    <line x1="12" y1="8" x2="12" y2="12"></line>
                                                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                                </svg>
                                                Research Gaps
                                                {!hasAtLeastTwoPapers ? (
                                                    <span className="mode-tab-badge disabled">Requires 2+ papers</span>
                                                ) : (
                                                    <span className="mode-tab-badge">2–4</span>
                                                )}
                                            </button>
                                        </div>

                                        {/* MODE 1: Single-Paper Ask */}
                                        {chatMode === 'ask' && (
                                            <>
                                                <div className="chat-selector-row">
                                                    <label htmlFor="ask-paper-select" className="chat-selector-label">
                                                        Ask about:
                                                    </label>
                                                    <select
                                                        id="ask-paper-select"
                                                        className="chat-paper-select"
                                                        value={selectedPaperId}
                                                        onChange={(e) => setSelectedPaperId(e.target.value)}
                                                        disabled={loadingAsk || loadingCompare || loadingGap}
                                                    >
                                                        {activeSession.papers.map((p) => (
                                                            <option key={p.id} value={p.id}>
                                                                {p.title}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>

                                                {/* Research Prompt Shortcuts for Single Paper */}
                                                <div className="prompt-shortcuts-row">
                                                    <span className="prompt-shortcuts-label">
                                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ opacity: 0.75 }}>
                                                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                                                        </svg>
                                                        Research prompts:
                                                    </span>
                                                    {SINGLE_PAPER_SHORTCUTS.map((item, idx) => (
                                                        <button
                                                            key={idx}
                                                            type="button"
                                                            className="prompt-shortcut-btn"
                                                            disabled={loadingAsk || loadingCompare || loadingGap}
                                                            onClick={() => setQuestionText(item.prompt)}
                                                            title={item.prompt}
                                                            aria-label={`Fill prompt: ${item.label}`}
                                                        >
                                                            {item.label}
                                                        </button>
                                                    ))}
                                                </div>

                                                {askError && (
                                                    <div className="alert-box error" style={{ marginBottom: '0.75rem' }}>
                                                        {askError}
                                                    </div>
                                                )}

                                                <div className="chat-input-row">
                                                    <textarea
                                                        className="chat-textarea"
                                                        placeholder="Ask a research question... (Shift+Enter for newline)"
                                                        value={questionText}
                                                        onChange={(e) => setQuestionText(e.target.value)}
                                                        onKeyDown={handleKeyDown}
                                                        disabled={loadingAsk || loadingCompare || loadingGap}
                                                        rows={2}
                                                    />
                                                    <button
                                                        className="chat-send-btn"
                                                        onClick={handleSendQuestion}
                                                        disabled={loadingAsk || loadingCompare || loadingGap || !questionText.trim() || !selectedPaperId}
                                                        title="Send question (Enter)"
                                                        type="button"
                                                    >
                                                        {loadingAsk ? (
                                                            <span className="spinner-icon-sm"></span>
                                                        ) : (
                                                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                                                            </svg>
                                                        )}
                                                        <span>Send</span>
                                                    </button>
                                                </div>
                                            </>
                                        )}

                                        {/* MODE 2: Multi-Paper Comparison */}
                                        {chatMode === 'compare' && (
                                            <>
                                                {/* Select 2-4 Papers for Comparison */}
                                                <div className="compare-selection-bar">
                                                    <div className="compare-selection-header">
                                                        <span className="compare-selection-title">
                                                            Select 2 to 4 papers to compare:
                                                        </span>
                                                        <span className={`compare-selection-count ${selectedComparisonPaperIds.length < 2 ? 'warn' : 'valid'}`}>
                                                            {selectedComparisonPaperIds.length}/4 selected
                                                            {selectedComparisonPaperIds.length < 2 && ' (minimum 2)'}
                                                        </span>
                                                    </div>

                                                    <div className="compare-papers-grid">
                                                        {activeSession.papers.map((p) => {
                                                            const isSelected = selectedComparisonPaperIds.includes(p.id);
                                                            const isMaxReached = selectedComparisonPaperIds.length >= 4 && !isSelected;

                                                            return (
                                                                <label
                                                                    key={p.id}
                                                                    className={`compare-paper-pill ${isSelected ? 'selected' : ''} ${isMaxReached ? 'disabled' : ''}`}
                                                                    title={isMaxReached ? 'Maximum 4 papers reached (deselect one first)' : p.title}
                                                                >
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={isSelected}
                                                                        disabled={loadingCompare || loadingGap || isMaxReached}
                                                                        onChange={() => handleToggleComparisonPaper(p.id)}
                                                                    />
                                                                    <span className="compare-paper-pill-title">{p.title}</span>
                                                                </label>
                                                            );
                                                        })}
                                                    </div>
                                                </div>

                                                {/* Research Prompt Shortcuts for Multi-Paper Comparison */}
                                                <div className="prompt-shortcuts-row">
                                                    <span className="prompt-shortcuts-label">
                                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ opacity: 0.75 }}>
                                                            <polyline points="16 3 21 3 21 8"></polyline>
                                                            <line x1="4" y1="20" x2="21" y2="3"></line>
                                                            <polyline points="21 16 21 21 16 21"></polyline>
                                                            <line x1="15" y1="15" x2="21" y2="21"></line>
                                                            <line x1="4" y1="4" x2="9" y2="9"></line>
                                                        </svg>
                                                        Comparison prompts:
                                                    </span>
                                                    {COMPARISON_SHORTCUTS.map((item, idx) => (
                                                        <button
                                                            key={idx}
                                                            type="button"
                                                            className="prompt-shortcut-btn"
                                                            disabled={loadingCompare || loadingAsk || loadingGap}
                                                            onClick={() => setComparisonQuestion(item.prompt)}
                                                            title={item.prompt}
                                                            aria-label={`Fill prompt: ${item.label}`}
                                                        >
                                                            {item.label}
                                                        </button>
                                                    ))}
                                                </div>

                                                {compareError && (
                                                    <div className="alert-box error" style={{ marginBottom: '0.75rem' }}>
                                                        {compareError}
                                                    </div>
                                                )}

                                                <div className="chat-input-row">
                                                    <textarea
                                                        className="chat-textarea"
                                                        placeholder="What would you like to compare? e.g. methodology, findings, limitations, and research gaps"
                                                        value={comparisonQuestion}
                                                        onChange={(e) => setComparisonQuestion(e.target.value)}
                                                        disabled={loadingCompare || loadingGap}
                                                        rows={2}
                                                    />
                                                    <button
                                                        className="chat-send-btn compare-btn"
                                                        onClick={handleGenerateComparison}
                                                        disabled={loadingCompare || loadingGap || loadingAsk || selectedComparisonPaperIds.length < 2 || selectedComparisonPaperIds.length > 4}
                                                        title="Generate cross-paper comparison"
                                                        type="button"
                                                    >
                                                        {loadingCompare ? (
                                                            <span className="spinner-icon-sm"></span>
                                                        ) : (
                                                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                <polyline points="16 3 21 3 21 8"></polyline>
                                                                <line x1="4" y1="20" x2="21" y2="3"></line>
                                                                <polyline points="21 16 21 21 16 21"></polyline>
                                                                <line x1="15" y1="15" x2="21" y2="21"></line>
                                                                <line x1="4" y1="4" x2="9" y2="9"></line>
                                                            </svg>
                                                        )}
                                                        <span>Generate Comparison</span>
                                                    </button>
                                                </div>
                                            </>
                                        )}

                                        {/* MODE 3: Multi-Paper Research Gap Analysis */}
                                        {chatMode === 'gap' && (
                                            <>
                                                {/* Select 2-4 Papers for Research Gap Analysis */}
                                                <div className="compare-selection-bar">
                                                    <div className="compare-selection-header">
                                                        <span className="compare-selection-title">
                                                            Select 2 to 4 papers to analyze gaps:
                                                        </span>
                                                        <span className={`compare-selection-count ${selectedGapPaperIds.length < 2 ? 'warn' : 'valid'}`}>
                                                            {selectedGapPaperIds.length}/4 selected
                                                            {selectedGapPaperIds.length < 2 && ' (minimum 2)'}
                                                        </span>
                                                    </div>

                                                    <div className="compare-papers-grid">
                                                        {activeSession.papers.map((p) => {
                                                            const isSelected = selectedGapPaperIds.includes(p.id);
                                                            const isMaxReached = selectedGapPaperIds.length >= 4 && !isSelected;

                                                            return (
                                                                <label
                                                                    key={p.id}
                                                                    className={`compare-paper-pill ${isSelected ? 'selected' : ''} ${isMaxReached ? 'disabled' : ''}`}
                                                                    title={isMaxReached ? 'Maximum 4 papers reached (deselect one first)' : p.title}
                                                                >
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={isSelected}
                                                                        disabled={loadingGap || loadingCompare || isMaxReached}
                                                                        onChange={() => handleToggleGapPaper(p.id)}
                                                                    />
                                                                    <span className="compare-paper-pill-title">{p.title}</span>
                                                                </label>
                                                            );
                                                        })}
                                                    </div>
                                                </div>

                                                {/* Research Prompt Shortcuts for Research Gap Analysis */}
                                                <div className="prompt-shortcuts-row">
                                                    <span className="prompt-shortcuts-label">
                                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ opacity: 0.75 }}>
                                                            <circle cx="12" cy="12" r="10"></circle>
                                                            <line x1="12" y1="8" x2="12" y2="12"></line>
                                                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                                        </svg>
                                                        Gap prompts:
                                                    </span>
                                                    {RESEARCH_GAP_SHORTCUTS.map((item, idx) => (
                                                        <button
                                                            key={idx}
                                                            type="button"
                                                            className="prompt-shortcut-btn"
                                                            disabled={loadingGap || loadingCompare || loadingAsk}
                                                            onClick={() => setGapQuestion(item.prompt)}
                                                            title={item.prompt}
                                                            aria-label={`Fill prompt: ${item.label}`}
                                                        >
                                                            {item.label}
                                                        </button>
                                                    ))}
                                                </div>

                                                {gapError && (
                                                    <div className="alert-box error" style={{ marginBottom: '0.75rem' }}>
                                                        {gapError}
                                                    </div>
                                                )}

                                                <div className="chat-input-row">
                                                    <textarea
                                                        className="chat-textarea"
                                                        placeholder="Identify the major research gaps, limitations, unanswered questions, and future research directions across these papers..."
                                                        value={gapQuestion}
                                                        onChange={(e) => setGapQuestion(e.target.value)}
                                                        disabled={loadingGap || loadingCompare}
                                                        rows={2}
                                                    />
                                                    <button
                                                        className="chat-send-btn gap-btn"
                                                        onClick={handleGenerateGapAnalysis}
                                                        disabled={loadingGap || loadingCompare || loadingAsk || selectedGapPaperIds.length < 2 || selectedGapPaperIds.length > 4}
                                                        title="Generate research gap analysis"
                                                        type="button"
                                                    >
                                                        {loadingGap ? (
                                                            <span className="spinner-icon-sm"></span>
                                                        ) : (
                                                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                <circle cx="12" cy="12" r="10"></circle>
                                                                <line x1="12" y1="8" x2="12" y2="12"></line>
                                                                <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                                            </svg>
                                                        )}
                                                        <span>Generate Research Gap Analysis</span>
                                                    </button>
                                                </div>
                                            </>
                                        )}
                                    </>
                                ) : (
                                    <div className="no-papers-chat-notice">
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                            <circle cx="12" cy="12" r="10"></circle>
                                            <line x1="12" y1="8" x2="12" y2="12"></line>
                                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                        </svg>
                                        <span>Add at least one paper to this research session before asking questions.</span>
                                        <button
                                            className="action-btn-secondary"
                                            style={{ marginLeft: 'auto', fontSize: '0.8rem' }}
                                            onClick={openAddPapersModal}
                                            type="button"
                                        >
                                            + Add Papers
                                        </button>
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </main>
            </div>

            {/* Add Papers Modal */}
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
                                className="action-btn-secondary"
                                onClick={() => setIsPapersModalOpen(false)}
                                disabled={savingPapers}
                                type="button"
                            >
                                Cancel
                            </button>
                            <button
                                className="action-btn-primary"
                                onClick={handleSaveSessionPapers}
                                disabled={savingPapers || projectPapers.length === 0}
                                type="button"
                            >
                                {savingPapers ? 'Saving...' : `Save Papers (${selectedModalPaperIds.length})`}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Reusable Confirmation Modal for Delete Session */}
            <DeleteModal
                isOpen={Boolean(deletingSession)}
                onClose={() => setDeletingSession(null)}
                onConfirm={handleConfirmDelete}
                title="Delete Research Session"
                message={`Are you sure you want to delete "${deletingSession?.title}"? All messages and evidence links in this session will be permanently removed.`}
                warning="This action cannot be undone. Associated papers and projects will not be deleted."
                isDeleting={isDeleting}
            />
        </div>
    );
}

export default ResearchWorkspace;
