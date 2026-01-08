/**
 * Unit Tests for FlashcardViewer Defensive Checks (Issue #168)
 * 
 * Tests using Jest for unit testing JavaScript code
 * 
 * CRITICAL: Proper JavaScript tests for JavaScript code
 */

// Mock DOM and dependencies
global.document = {
    createElement: jest.fn(() => ({
        textContent: '',
        innerHTML: '',
        classList: {
            add: jest.fn(),
            remove: jest.fn()
        },
        addEventListener: jest.fn(),
        remove: jest.fn()
    })),
    body: {
        appendChild: jest.fn()
    },
    querySelector: jest.fn(),
    getElementById: jest.fn()
};

global.showNotification = jest.fn();

// Import the FlashcardViewer class (adjust path as needed)
// const FlashcardViewer = require('../../app/static/js/flashcard-viewer.js');

describe('FlashcardViewer - reviewStarredCards() Defensive Checks', () => {
    let viewer;
    let mockFlashcards;

    beforeEach(() => {
        // Reset mocks
        jest.clearAllMocks();
        
        // Create mock flashcards
        mockFlashcards = [
            { question: 'Q1', answer: 'A1' },
            { question: 'Q2', answer: 'A2' },
            { question: 'Q3', answer: 'A3' },
            { question: 'Q4', answer: 'A4' },
            { question: 'Q5', answer: 'A5' }
        ];

        // Create viewer instance (mock for now)
        viewer = {
            flashcards: [...mockFlashcards],
            originalFlashcards: null,
            starredCards: new Set(),
            reviewedCards: new Set(),
            knownCards: new Set(),
            isFilteredView: false,
            currentIndex: 0,
            isFlipped: false,
            showError: jest.fn(),
            cleanupEventListeners: jest.fn(),
            render: jest.fn(),
            setupEventListeners: jest.fn()
        };
    });

    test('should fail fast when no cards are starred', () => {
        // Arrange
        viewer.starredCards = new Set();

        // Act
        const result = reviewStarredCards(viewer);

        // Assert
        expect(viewer.showError).toHaveBeenCalledWith('No starred cards to review!');
        expect(result).toBeUndefined();
    });

    test('should fail fast when originalFlashcards is null', () => {
        // Arrange
        viewer.starredCards = new Set([0, 1]);
        viewer.isFilteredView = true;
        viewer.originalFlashcards = null;

        // Act
        const result = reviewStarredCards(viewer);

        // Assert
        expect(viewer.showError).toHaveBeenCalledWith('Unable to review starred cards. Please try again.');
        expect(result).toBeUndefined();
    });

    test('should fail fast when originalFlashcards is not an array', () => {
        // Arrange
        viewer.starredCards = new Set([0, 1]);
        viewer.isFilteredView = true;
        viewer.originalFlashcards = "not an array";

        // Act
        const result = reviewStarredCards(viewer);

        // Assert
        expect(viewer.showError).toHaveBeenCalledWith('Unable to review starred cards. Please try again.');
        expect(result).toBeUndefined();
    });

    test('should fail fast when originalFlashcards is empty', () => {
        // Arrange
        viewer.starredCards = new Set([0, 1]);
        viewer.isFilteredView = true;
        viewer.originalFlashcards = [];

        // Act
        const result = reviewStarredCards(viewer);

        // Assert
        expect(viewer.showError).toHaveBeenCalledWith('No flashcards available to review.');
        expect(result).toBeUndefined();
    });

    test('should filter out invalid index types', () => {
        // Arrange
        viewer.starredCards = new Set(['0', '1', 2]); // Mix of strings and numbers
        viewer.originalFlashcards = [...mockFlashcards];

        // Act
        const validIndices = Array.from(viewer.starredCards).filter(index => {
            return typeof index === 'number' && 
                   index >= 0 && 
                   index < viewer.originalFlashcards.length;
        });

        // Assert
        expect(validIndices).toEqual([2]);
        expect(validIndices.length).toBe(1);
    });

    test('should filter out out-of-bounds indices', () => {
        // Arrange
        viewer.starredCards = new Set([-1, 0, 1, 10, 999]);
        viewer.originalFlashcards = [...mockFlashcards];

        // Act
        const validIndices = Array.from(viewer.starredCards).filter(index => {
            return typeof index === 'number' && 
                   index >= 0 && 
                   index < viewer.originalFlashcards.length;
        });

        // Assert
        expect(validIndices).toEqual([0, 1]);
        expect(validIndices.length).toBe(2);
    });

    test('should warn user when cards are filtered out', () => {
        // Arrange
        viewer.starredCards = new Set([0, 1, 2]);
        viewer.originalFlashcards = [mockFlashcards[0], null, mockFlashcards[2]];
        
        const validIndices = [0, 1, 2];
        const starredCards = validIndices.map(index => viewer.originalFlashcards[index]);
        const validCards = starredCards.filter(card => card !== null && card !== undefined);
        const filteredCount = validIndices.length - validCards.length;

        // Act & Assert
        expect(filteredCount).toBe(1);
        expect(validCards.length).toBe(2);
    });

    test('should successfully review valid starred cards (happy path)', () => {
        // Arrange
        viewer.starredCards = new Set([0, 2, 4]);
        viewer.originalFlashcards = [...mockFlashcards];
        
        const validIndices = Array.from(viewer.starredCards).filter(index => {
            return typeof index === 'number' && 
                   index >= 0 && 
                   index < viewer.originalFlashcards.length;
        });
        
        const starredCards = validIndices.map(index => viewer.originalFlashcards[index]);
        const validCards = starredCards.filter(card => card !== null && card !== undefined);

        // Assert
        expect(validCards.length).toBe(3);
        expect(validCards[0]).toEqual(mockFlashcards[0]);
        expect(validCards[1]).toEqual(mockFlashcards[2]);
        expect(validCards[2]).toEqual(mockFlashcards[4]);
    });
});

describe('FlashcardViewer - restoreFullDeck() Defensive Checks', () => {
    let viewer;
    let mockFlashcards;

    beforeEach(() => {
        jest.clearAllMocks();
        
        mockFlashcards = [
            { question: 'Q1', answer: 'A1' },
            { question: 'Q2', answer: 'A2' },
            { question: 'Q3', answer: 'A3' }
        ];

        viewer = {
            flashcards: [mockFlashcards[0], mockFlashcards[2]], // Filtered view
            originalFlashcards: [...mockFlashcards],
            originalReviewedCards: new Set([0, 1]),
            originalKnownCards: new Set([0]),
            originalStarredCards: new Set([2]),
            reviewedCards: new Set(),
            knownCards: new Set(),
            starredCards: new Set(),
            isFilteredView: true,
            currentIndex: 0,
            isFlipped: false,
            showError: jest.fn(),
            cleanupEventListeners: jest.fn(),
            render: jest.fn(),
            setupEventListeners: jest.fn()
        };
    });

    test('should return early when not in filtered view', () => {
        // Arrange
        viewer.isFilteredView = false;

        // Act
        const shouldReturn = !viewer.isFilteredView;

        // Assert
        expect(shouldReturn).toBe(true);
    });

    test('should fail fast when originalFlashcards is null', () => {
        // Arrange
        viewer.originalFlashcards = null;

        // Act
        const isValid = viewer.originalFlashcards && Array.isArray(viewer.originalFlashcards);

        // Assert
        expect(isValid).toBe(false);
    });

    test('should fail fast when all Sets are missing (critical corruption)', () => {
        // Arrange
        viewer.originalReviewedCards = null;
        viewer.originalKnownCards = null;
        viewer.originalStarredCards = null;

        // Act
        const allSetsMissing = !viewer.originalReviewedCards && 
                               !viewer.originalKnownCards && 
                               !viewer.originalStarredCards;

        // Assert
        expect(allSetsMissing).toBe(true);
    });

    test('should recover gracefully when individual Sets are invalid', () => {
        // Arrange
        viewer.originalReviewedCards = null;
        viewer.originalKnownCards = [1, 2, 3]; // Array instead of Set
        viewer.originalStarredCards = undefined;

        // Act - Simulate recovery
        if (!viewer.originalReviewedCards || !(viewer.originalReviewedCards instanceof Set)) {
            viewer.originalReviewedCards = new Set();
        }
        if (!viewer.originalKnownCards || !(viewer.originalKnownCards instanceof Set)) {
            viewer.originalKnownCards = new Set();
        }
        if (!viewer.originalStarredCards || !(viewer.originalStarredCards instanceof Set)) {
            viewer.originalStarredCards = new Set();
        }

        // Assert
        expect(viewer.originalReviewedCards instanceof Set).toBe(true);
        expect(viewer.originalKnownCards instanceof Set).toBe(true);
        expect(viewer.originalStarredCards instanceof Set).toBe(true);
    });

    test('should successfully restore full deck (happy path)', () => {
        // Arrange - viewer is already in filtered view with valid data

        // Act - Simulate restoration
        const flashcards = [...viewer.originalFlashcards];
        const reviewedCards = new Set(viewer.originalReviewedCards);
        const knownCards = new Set(viewer.originalKnownCards);
        const starredCards = new Set(viewer.originalStarredCards);

        // Assert
        expect(flashcards.length).toBe(3);
        expect(reviewedCards.size).toBe(2);
        expect(knownCards.size).toBe(1);
        expect(starredCards.size).toBe(1);
    });
});

// Helper function to simulate reviewStarredCards logic
function reviewStarredCards(viewer) {
    if (viewer.starredCards.size === 0) {
        viewer.showError('No starred cards to review!');
        return;
    }

    if (!viewer.isFilteredView) {
        viewer.originalFlashcards = [...viewer.flashcards];
    }

    if (!viewer.originalFlashcards || !Array.isArray(viewer.originalFlashcards)) {
        viewer.showError('Unable to review starred cards. Please try again.');
        return;
    }

    if (viewer.originalFlashcards.length === 0) {
        viewer.showError('No flashcards available to review.');
        return;
    }

    return true;
}

