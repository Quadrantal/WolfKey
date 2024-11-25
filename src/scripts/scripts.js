// Handle header visibility on scroll
let lastScroll = 0;
window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    const header = document.querySelector('.top-nav');
    
    if (currentScroll <= 0) {
        header.classList.remove('nav-hidden');
        return;
    }
    
    if (currentScroll > lastScroll && !header.classList.contains('nav-hidden')) {
        header.classList.add('nav-hidden');
    } else if (currentScroll < lastScroll && header.classList.contains('nav-hidden')) {
        header.classList.remove('nav-hidden');
    }
    lastScroll = currentScroll;
});

// Handle new question submission
document.getElementById('questionForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const title = document.getElementById('title').value;
    const question = document.getElementById('question').value;
    const subject = document.getElementById('subject').value;
    
    // Create new question post
    const newPost = createQuestionPost(title, question);
    document.getElementById('questionsFeed').prepend(newPost);
    
    // Clear form
    this.reset();
});

function createQuestionPost(title, content) {
    const post = document.createElement('div');
    post.className = 'post';
    post.innerHTML = `
        <div class="post-header">
            <h3>${title}</h3>
            <span class="timestamp">Just now</span>
        </div>
        <div class="post-content">
            <p>${content}</p>
        </div>
        <div class="vote-buttons">
            <button onclick="upvote(this)">👍 <span>0</span></button>
            <button onclick="downvote(this)">👎 <span>0</span></button>
        </div>
        <button onclick="toggleAnswerForm(this)">Answer</button>
        <div class="answer-form" style="display: none;">
            <textarea placeholder="Write your answer..." rows="4"></textarea>
            <button onclick="submitAnswer(this)">Submit Answer</button>
        </div>
        <div class="answers"></div>
    `;
    return post;
}

function toggleAnswerForm(button) {
    const form = button.nextElementSibling;
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
    if (form.style.display === 'block') {
        form.style.opacity = '0';
        setTimeout(() => form.style.opacity = '1', 10);
    }
}

function submitAnswer(button) {
    const textarea = button.previousElementSibling;
    const answer = textarea.value;
    if (!answer.trim()) return;

    const answersDiv = button.parentElement.nextElementSibling;
    const answerPost = document.createElement('div');
    answerPost.className = 'post';
    answerPost.style.opacity = '0';
    answerPost.innerHTML = `
        <p>${answer}</p>
        <div class="vote-buttons">
            <button onclick="upvote(this)">👍 <span>0</span></button>
            <button onclick="downvote(this)">👎 <span>0</span></button>
        </div>
    `;
    answersDiv.prepend(answerPost);
    
    // Animate the new answer
    setTimeout(() => answerPost.style.opacity = '1', 10);
    
    // Clear and hide form
    textarea.value = '';
    button.parentElement.style.display = 'none';
}

function upvote(button) {
    if (button.classList.contains('voted')) {
        // Remove vote
        const span = button.querySelector('span');
        span.textContent = parseInt(span.textContent) - 1;
        button.classList.remove('voted');
    } else {
        // Add vote and remove downvote if exists
        const span = button.querySelector('span');
        span.textContent = parseInt(span.textContent) + 1;
        button.classList.add('voted');
        
        const downvoteButton = button.nextElementSibling;
        if (downvoteButton && downvoteButton.classList.contains('voted')) {
            const downSpan = downvoteButton.querySelector('span');
            downSpan.textContent = parseInt(downSpan.textContent) - 1;
            downvoteButton.classList.remove('voted');
        }
    }
    button.classList.add('vote-active');
    setTimeout(() => button.classList.remove('vote-active'), 400);
}

function downvote(button) {
    if (button.classList.contains('voted')) {
        // Remove vote
        const span = button.querySelector('span');
        span.textContent = parseInt(span.textContent) - 1;
        button.classList.remove('voted');
    } else {
        // Add vote and remove upvote if exists
        const span = button.querySelector('span');
        span.textContent = parseInt(span.textContent) + 1;
        button.classList.add('voted');
        
        const upvoteButton = button.previousElementSibling;
        if (upvoteButton && upvoteButton.classList.contains('voted')) {
            const upSpan = upvoteButton.querySelector('span');
            upSpan.textContent = parseInt(upSpan.textContent) - 1;
            upvoteButton.classList.remove('voted');
        }
    }
    button.classList.add('vote-active');
    setTimeout(() => button.classList.remove('vote-active'), 400);
}


document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    
    // Check for saved theme preference or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    themeToggle.checked = savedTheme === 'dark';

    // Handle theme toggle
    themeToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    });
});