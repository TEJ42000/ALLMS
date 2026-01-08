/**
 * Flashcard Page Controller
 * 
 * Manages the flashcard sets page, including:
 * - Loading and displaying flashcard sets
 * - Starting flashcard study sessions
 * - Navigation between sets and viewer
 * 
 * HIGH FIX: Moved from inline script for CSP compliance
 */

// Flashcard data and initialization
let flashcardViewer = null;

// Sample flashcard sets (replace with API call in Phase 2)
const flashcardSets = [
    {
        id: 1,
        title: "ECHR Fundamentals",
        description: "Basic concepts and principles of the European Convention on Human Rights",
        cardCount: 20,
        cards: [
            { question: "What does ECHR stand for?", answer: "European Convention on Human Rights" },
            { question: "When was the ECHR adopted?", answer: "November 4, 1950" },
            { question: "How many articles are in the ECHR?", answer: "59 articles" },
            { question: "What is Article 2 of the ECHR?", answer: "Right to life" },
            { question: "What is Article 3 of the ECHR?", answer: "Prohibition of torture" },
            { question: "What is Article 5 of the ECHR?", answer: "Right to liberty and security" },
            { question: "What is Article 6 of the ECHR?", answer: "Right to a fair trial" },
            { question: "What is Article 8 of the ECHR?", answer: "Right to respect for private and family life" },
            { question: "What is Article 10 of the ECHR?", answer: "Freedom of expression" },
            { question: "What is Article 11 of the ECHR?", answer: "Freedom of assembly and association" },
            { question: "Where is the European Court of Human Rights located?", answer: "Strasbourg, France" },
            { question: "How many judges are on the European Court of Human Rights?", answer: "One judge per member state" },
            { question: "What is the principle of subsidiarity in ECHR?", answer: "National authorities are primarily responsible for protecting rights" },
            { question: "What is the margin of appreciation?", answer: "Discretion given to states in implementing Convention rights" },
            { question: "What is a derogation under ECHR?", answer: "Temporary suspension of certain rights in emergencies" },
            { question: "What is Article 14 of the ECHR?", answer: "Prohibition of discrimination" },
            { question: "What is Protocol 1, Article 1?", answer: "Protection of property" },
            { question: "What is the 'living instrument' doctrine?", answer: "ECHR is interpreted in light of present-day conditions" },
            { question: "What is the exhaustion of domestic remedies rule?", answer: "Applicants must use all available national remedies before applying to ECtHR" },
            { question: "What is a pilot judgment?", answer: "Judgment addressing systemic issues affecting many cases" }
        ]
    },
    {
        id: 2,
        title: "Legal Terminology",
        description: "Essential legal terms and definitions",
        cardCount: 15,
        cards: [
            { term: "Tort", definition: "A civil wrong that causes harm or loss" },
            { term: "Plaintiff", definition: "The party who initiates a lawsuit" },
            { term: "Defendant", definition: "The party being sued or accused" },
            { term: "Burden of proof", definition: "The obligation to prove one's assertion" },
            { term: "Precedent", definition: "A legal decision that serves as an authoritative rule in future cases" },
            { term: "Jurisdiction", definition: "The authority of a court to hear and decide a case" },
            { term: "Statute", definition: "A written law passed by a legislative body" },
            { term: "Common law", definition: "Law developed through judicial decisions rather than statutes" },
            { term: "Equity", definition: "A system of law based on fairness and justice" },
            { term: "Injunction", definition: "A court order requiring a party to do or refrain from doing something" },
            { term: "Damages", definition: "Monetary compensation for loss or injury" },
            { term: "Liability", definition: "Legal responsibility for one's actions or omissions" },
            { term: "Negligence", definition: "Failure to exercise reasonable care" },
            { term: "Breach", definition: "Violation of a law, obligation, or agreement" },
            { term: "Remedy", definition: "Legal means to enforce a right or redress a wrong" }
        ]
    },
    {
        id: 3,
        title: "Case Law Essentials",
        description: "Important cases and their holdings",
        cardCount: 10,
        cards: [
            { question: "What was the holding in Handyside v UK (1976)?", answer: "Freedom of expression includes information that may offend, shock, or disturb" },
            { question: "What principle was established in Sunday Times v UK (1979)?", answer: "Restrictions on freedom of expression must be prescribed by law" },
            { question: "What was decided in Soering v UK (1989)?", answer: "Extradition may violate Article 3 if it exposes person to inhuman treatment" },
            { question: "What did McCann v UK (1995) establish?", answer: "Use of lethal force must be absolutely necessary" },
            { question: "What was the outcome of Pretty v UK (2002)?", answer: "No right to die under Article 2" },
            { question: "What principle came from Tyrer v UK (1978)?", answer: "Corporal punishment violates Article 3" },
            { question: "What was decided in Golder v UK (1975)?", answer: "Right of access to court is implicit in Article 6" },
            { question: "What did Marckx v Belgium (1979) establish?", answer: "Discrimination against children born out of wedlock violates Article 8" },
            { question: "What was the holding in Dudgeon v UK (1981)?", answer: "Criminalization of homosexual acts violates Article 8" },
            { question: "What principle was established in Airey v Ireland (1979)?", answer: "Effective access to court may require legal aid" }
        ]
    }
];

// Load flashcard sets on page load
document.addEventListener('DOMContentLoaded', function() {
    loadFlashcardSets();
    setupBackButton();
});

/**
 * Load and display flashcard sets
 */
function loadFlashcardSets() {
    const setsContainer = document.querySelector('.sets-grid');
    
    if (!setsContainer) {
        console.error('[FlashcardPage] Sets container not found');
        return;
    }
    
    if (flashcardSets.length === 0) {
        setsContainer.innerHTML = '<p class="no-sets">No flashcard sets available yet.</p>';
        return;
    }

    setsContainer.innerHTML = flashcardSets.map(set => `
        <div class="flashcard-set-card" data-set-id="${set.id}">
            <div class="set-icon" aria-hidden="true">📚</div>
            <h3>${escapeHtml(set.title)}</h3>
            <p>${escapeHtml(set.description)}</p>
            <div class="set-meta">
                <span class="card-count">${set.cardCount} cards</span>
            </div>
            <button class="btn-study" data-set-id="${set.id}" aria-label="Start studying ${escapeHtml(set.title)}">
                Start Studying
            </button>
        </div>
    `).join('');

    // HIGH FIX: Use event delegation instead of inline onclick
    setsContainer.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-study')) {
            const setId = parseInt(e.target.getAttribute('data-set-id'));
            startFlashcards(setId);
        }
    });
}

/**
 * Start studying a flashcard set
 */
function startFlashcards(setId) {
    const set = flashcardSets.find(s => s.id === setId);
    if (!set) {
        console.error('[FlashcardPage] Flashcard set not found:', setId);
        return;
    }

    // Hide sets, show viewer
    const setsElement = document.getElementById('flashcard-sets');
    const viewerContainer = document.getElementById('flashcard-viewer-container');
    const setTitle = document.getElementById('set-title');
    
    if (!setsElement || !viewerContainer || !setTitle) {
        console.error('[FlashcardPage] Required elements not found');
        return;
    }
    
    setsElement.style.display = 'none';
    viewerContainer.style.display = 'block';
    setTitle.textContent = set.title;

    // Initialize flashcard viewer
    if (flashcardViewer) {
        flashcardViewer.cleanup();
    }

    try {
        flashcardViewer = new FlashcardViewer('flashcard-viewer', set.cards);
        window.flashcardViewer = flashcardViewer;
    } catch (error) {
        console.error('[FlashcardPage] Error initializing flashcard viewer:', error);
        alert('Failed to start flashcard viewer. Please try again.');
    }
}

/**
 * Setup back button
 */
function setupBackButton() {
    const btnBack = document.getElementById('btn-back-to-sets');
    if (!btnBack) {
        console.warn('[FlashcardPage] Back button not found');
        return;
    }
    
    btnBack.addEventListener('click', function() {
        // Cleanup viewer
        if (flashcardViewer) {
            flashcardViewer.cleanup();
            flashcardViewer = null;
        }

        // Show sets, hide viewer
        const setsElement = document.getElementById('flashcard-sets');
        const viewerContainer = document.getElementById('flashcard-viewer-container');
        
        if (setsElement && viewerContainer) {
            setsElement.style.display = 'block';
            viewerContainer.style.display = 'none';
        }
    });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

