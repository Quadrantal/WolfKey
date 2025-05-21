// static/forum/js/modules/voting-system.js

export class VotingSystem {
    constructor(csrfToken) {
        this.csrfToken = csrfToken;
        this.initializeVoting();
    }

    initializeVoting() {
        document.querySelectorAll('.vote-button').forEach(button => {
            button.addEventListener('click', this.handleVote.bind(this));
        });
    }

    async handleVote(event) {
        event.preventDefault();
        const form = event.currentTarget.closest('form');
        if (!form) {
            console.error("Form not found for the vote button");
            return;
        }

        const url = form.getAttribute('action');
        const solutionIdInput = form.querySelector('input[name="solution_id"]');
        const voteTypeInput = form.querySelector('input[name="action"]');

        if (!solutionIdInput || !voteTypeInput) {
            console.error("Solution ID or action input not found in the form");
            return;
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    solution_id: solutionIdInput.value,
                    action: voteTypeInput.value
                })
            });

            if (!response.ok) {
                const data = await response.json();
                if (data && data.message) {
                    alert(data.message);
                } else {
                    alert('An unexpected error occurred.');
                }
                throw new Error(data.message || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.success) {
                this.updateVoteUI(form, data);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    updateVoteUI(form, data) {
        const voteCell = form.closest('.vote-cell');
        const voteCount = voteCell.querySelector('.vote-count');
        if (voteCount) {
            voteCount.textContent = data.upvotes - data.downvotes;
        }
        
        const upvoteButton = voteCell.querySelector('form[action*="upvote"] button');
        const downvoteButton = voteCell.querySelector('form[action*="downvote"] button');
        
        upvoteButton.classList.remove('voted-up');
        downvoteButton.classList.remove('voted-down');
        
        if (data.vote_state === 'upvoted') {
            upvoteButton.classList.add('voted-up');
        } else if (data.vote_state === 'downvoted') {
            downvoteButton.classList.add('voted-down');
        }
    }
}