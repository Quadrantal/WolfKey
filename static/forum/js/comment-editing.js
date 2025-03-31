export class CommentEditor {
    constructor(editorManager, csrfToken) {
        this.editorManager = editorManager;
        this.csrfToken = csrfToken;
        this.showReplyForm = this.showReplyForm.bind(this);
        this.submitComment = this.submitComment.bind(this);
        this.cancelComment = this.cancelComment.bind(this);
        this.saveCommentEdit = this.saveCommentEdit.bind(this);
        this.cancelCommentEdit = this.cancelCommentEdit.bind(this);
        this.originalContents = {};

        this.bindEvents();
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            const button = e.target.closest('button'); 
            if (!button) return; // Ignore clicks outside buttons


            if (button.matches('.reply-button')) {
                const solutionId = Number(button.dataset.solutionId);
                const parentId = button.dataset.parentId || null;
                this.showReplyForm(solutionId, parentId);
            }
            if (button.matches('.edit-comment')) {
                const commentId = Number(button.dataset.commentId);
                this.showEditForm(commentId);
            }
            if (button.matches('.save-comment')) {
                const commentId = Number(button.dataset.commentId);
                this.saveCommentEdit(commentId);
            }
            if (button.matches('.cancel-comment')) {
                const commentId = Number(button.dataset.commentId);
                this.cancelCommentEdit(commentId);
            }
            if (button.matches('.delete-comment')) {
                const commentId = Number(button.dataset.commentId);
                this.deleteComment(commentId);
            }
        });
    }

    async showReplyForm(solutionId, parentId = null) {
        const formId = `comment-form-${solutionId}-${parentId || 'root'}`;
        const container = document.createElement('div');
        container.id = formId;
        container.className = 'comment-form-container';

        
        container.innerHTML = `
            <div id="editorjs-${formId}" class="comment-editor"></div>
            <div class="comment-actions">
                <button class="btn btn-primary btn-sm submit-comment">Submit</button>
                <button class="btn btn-secondary btn-sm cancel-comment">Cancel</button>
            </div>
        `;

        const target = parentId ? 
        document.querySelector(`#comment-${parentId} .replies`) :
        document.querySelector(`[data-solution-id="${solutionId}"] .comments`);
    
        if (!target) {
            console.error(`Could not find target container for solution ${solutionId}`);
            return;
        }
        
        target.appendChild(container);

        const editor = await this.editorManager.initializeCommentFormEditor(
            `editorjs-${formId}`, 
            this.csrfToken
        );
        this.editorManager.editors.set(formId, editor);

        container.querySelector('.submit-comment').addEventListener('click', () => 
            this.submitComment(solutionId, parentId, formId));
        container.querySelector('.cancel-comment').addEventListener('click', () => 
            this.cancelComment(formId));
    }

    async submitComment(solutionId, parentId, formId) {
        const editor = this.editorManager.editors.get(formId);
        if (!editor) return;

        try {
            const content = await editor.save();
            const response = await fetch(`/comment/create/${solutionId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    content,
                    parent_id: parentId
                })
            });

            if (response.ok) {
                const data = await response.json();
                
                if (data.messages) {
                    data.messages.forEach(messageData => {
                        showMessage(messageData.message, messageData.tags);
                    });
                }
                this.removeCommentForm(formId);
                this.refreshComments(solutionId);
            }
        } catch (error) {
            console.error('Error submitting comment:', error);
        }
    }

    cancelComment(formId) {
        this.removeCommentForm(formId);
    }

    removeCommentForm(formId) {
        const container = document.getElementById(formId);
        if (container) {
            container.remove();
        }
        this.editorManager.editors.delete(formId);
    }

    async refreshComments(solutionId) {
        try {
            const response = await fetch(`/solution/${solutionId}/comments/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to fetch comments');
            }
            
            const data = await response.json();
            const commentsContainer = document.querySelector(`[data-solution-id="${solutionId}"] .comments`);


            
            if (commentsContainer) {
                // Update HTML
                commentsContainer.innerHTML = data.html;
                
            
                // Initialize editors using the comments data
                if (data.comments && data.comments.length > 0) {
                    await this.editorManager.initializeCommentEditors(data.comments, this.csrfToken);
                    
                    // Reinitialize math fields
                    data.comments.forEach(comment => {

                        this.reinitMathFields(comment.id);

                    });
                }
            }
        } catch (error) {
            console.error('Error refreshing comments:', error);
        }
    }

    async showEditForm(commentId) {
        try {
            await this.editorManager.toggleEditorReadOnly(commentId, false);
            const editor = this.editorManager.editors.get(commentId);
            if (editor) {
                const content = await editor.save();
                this.originalContents[commentId] = content;
            }
            this.editorManager.editors.set(commentId, editor);

            this.toggleCommentActions(commentId, true);
            this.reinitMathFields(commentId);
        } catch (error) {
            console.error('Error enabling edit mode:', error);
        }
    }

    toggleCommentActions(commentId, isEditing) {
        const commentContainer = document.querySelector(`#comment-${commentId}`);
        if (!commentContainer) return;
    
        const defaultActions = commentContainer.querySelector('.default-actions');
        const editActions = commentContainer.querySelector('.edit-actions');
    
        if (defaultActions) {
            defaultActions.style.cssText = isEditing ? 'display: none !important;' : 'display: block !important;';
        }
        if (editActions) {
            editActions.style.cssText = isEditing ? 'display: block !important;' : 'display: none !important;';
        }
    }

    async saveCommentEdit(commentId) {
        const editor = this.editorManager.editors.get(commentId);
        if (!editor) return;

        try {
            const content = await editor.save();
            const response = await fetch(`/comment/edit/${commentId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ content })
            });

            const data = await response.json();
            if (data.messages) {
                data.messages.forEach(messageData => {
                    showMessage(messageData.message, messageData.tags);
                });
            }


            if (response.ok) {
                await this.editorManager.toggleEditorReadOnly(commentId, true);
                this.toggleCommentActions(commentId, false);
                delete this.originalContents[commentId];
                this.reinitMathFields(commentId);
            } else {
                console.error('Failed to save comment');
            }
        } catch (error) {
            console.error('Error saving comment:', error);
        }
    }

    async cancelCommentEdit(commentId) {
        const editor = this.editorManager.editors.get(commentId);
        if (editor && this.originalContents[commentId]) {
            try {
                // Restore original content
                await editor.render(this.originalContents[commentId]);
                
                // Reset editor state
                await this.editorManager.toggleEditorReadOnly(`editorjs-comment-${commentId}`, true);
                this.toggleCommentActions(commentId, false);
                
                // Cleanup
                delete this.originalContents[commentId];
                
                // Reinitialize math fields if present
                this.reinitMathFields(commentId);
            } catch (error) {
                console.error('Error canceling comment edit:', error);
            }
        }
    }

    async deleteComment(commentId) {
        if (!confirm('Are you sure you want to delete this comment?')) {
            return;
        }
    
        try {
            const response = await fetch(`/comment/delete/${commentId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                }
            });
    
            const data = await response.json();
    
            if (data.messages) {
                data.messages.forEach(messageData => {
                    showMessage(messageData.message, messageData.tags);
                });
            }
    
            if (response.ok) {
                const commentContainer = document.querySelector(`#comment-${commentId}`);
                if (commentContainer) {
                    const solutionContainer = commentContainer.closest('[data-solution-id]');
                    const solutionId = solutionContainer?.dataset.solutionId;
                    
                    // Remove the comment from DOM
                    commentContainer.remove();
                    
                    if (solutionId) {
                        await this.refreshComments(solutionId);
                    }
                }
            }
        } catch (error) {
            console.error('Delete comment failed:', error);
            showMessage('Failed to delete comment', 'error');
        }
    }

    reinitMathFields(commentId) {
        setTimeout(() => {
            const container = document.querySelector(`#editorjs-comment-${commentId}`);
            if (!container) return;

            container.querySelectorAll('.inline-math').forEach(elem => {
                const existingMathField = elem.querySelector('math-field');
                if (existingMathField) {
                    existingMathField.remove();
                }

                const tex = elem.getAttribute('data-tex');
                if (tex) {
                    const mathField = new MathfieldElement();
                    mathField.value = tex;
                    
                    const editor = this.editorManager.editors.get(commentId);
                    if (editor?.readOnly?.isEnabled) {
                        mathField.setAttribute('read-only', '');
                    }
                    
                    elem.appendChild(mathField);
                }
            });
        }, 100);
    }
}