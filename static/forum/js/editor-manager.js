// static/forum/js/modules/editor-manager.js

export class EditorManager {
    constructor() {
        this.editors = new Map();
    }

    async initializeMainEditor(editorId, content, csrfToken, readOnly = true) {
        try {
            const editor = createEditor(editorId, content, csrfToken, readOnly);
            this.editors.set('main', editor);
            return editor;
        } catch (error) {
            console.error('Error initializing main editor:', error);
            throw error;
        }
    }

    async initializeSolutionEditors(solutions, csrfToken) {
        try {
            solutions.forEach(solution => {
                try {
                    const editor = createEditor(
                        `editorjs-solution-${solution.id}`,
                        solution.content,
                        csrfToken,
                        true
                    );
                    this.editors.set(solution.id, editor);
                } catch (solutionError) {
                    console.error(`Error initializing solution ${solution.id}:`, solutionError);
                }
            });
        } catch (error) {
            console.error('Error initializing solution editors:', error);
            throw error;
        }
    }

    async initializeCommentEditors(comments, csrfToken) {
        try {
            comments.forEach(comment => {
                try {
                    const editor = createEditor(
                        `editorjs-comment-${comment.id}`,
                        comment.content,
                        csrfToken,
                        true
                    );
                    this.editors.set(comment.id, editor);
                } catch (commentError) {
                    console.error(`Error initializing solution ${solution.id}:`, commentError);
                }
            });
        } catch (error) {
            console.error('Error initializing comment editors:', error);
            throw error;
        }
    }

    async initializeSolutionFormEditor(editorId, csrfToken, contentFieldId) {
        
        try {
            const editor = createEditor(
                editorId,
                {},
                csrfToken,
                false,
                contentFieldId
            );
            this.editors.set('solution-form', editor);
            return editor;
        } catch (error) {
            console.error('Error initializing solution form editor:', error);
            throw error;
        }
    }
    async initializeCommentFormEditor(editorId, csrfToken) {
        try {
            const editor = createEditor(
                editorId,
                {},
                csrfToken,
                false
            );
            this.editors.set(editorId, editor);
            return editor;
        } catch (error) {
            console.error('Error initializing comment form editor:', error);
            throw error;
        }
    }


    getEditor(id) {
        return this.editors.get(id);
    }

    toggleEditorReadOnly(editorId, readOnly) {

        const id = Number(editorId);
        const editor = this.getEditor(id);
        if (editor) {
            editor.readOnly.toggle(readOnly);
        }

    }
}