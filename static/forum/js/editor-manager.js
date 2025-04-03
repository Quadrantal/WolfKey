// static/forum/js/editor-manager.js
import createEditor from './editor-config.js';
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
        const editor = this.getEditor(editorId);
        if (editor) {
            editor.readOnly.toggle(readOnly);
            // Access the holder element o
            // f the editor
            const holder = editor.configuration.holder; // Get the holder element from the editor instance
            if (typeof holder === 'string') {
                // If the holder is a string (ID), get the element by ID
                const holderElement = document.getElementById(holder);
                if (holderElement) {
                    this.updateMathFields(holderElement, readOnly, editor);
                } else {
                    console.warn(`Holder element with ID '${holder}' not found.`);
                }
            } else if (holder instanceof HTMLElement) {
                // If the holder is already an HTMLElement, use it directly
                this.updateMathFields(holder, readOnly, editor);
            } else {
                console.warn(`Invalid holder configuration for editor with ID '${editorId}'.`);
            }
        } else {
            console.warn(`Editor with ID '${editorId}' not found.`);
        }
    }
    
    updateMathFields(holder, readOnly, editor) {
        setTimeout(() => {
            holder.querySelectorAll('math-field').forEach(mathField => {
                const tex = mathField.value;
    
                if (tex) {
                    const mathElement = new MathfieldElement();
                    mathElement.value = tex;
    
                    // If the editor is in read-only mode, set the math field to read-only
                    if (readOnly) {
                        mathElement.readOnly = true;
                    }
    
                    // Find the block element containing the math-field
                    const blockElement = mathField.closest('.ce-block'); // Adjust the selector if needed
                    if (blockElement) {
                        const blockId = blockElement.getAttribute('data-id'); // Get the block's data-id attribute
                        if (blockId) {
                            // Add an event listener to the math-field for changes
                            mathElement.addEventListener("input", () => {
                                editor.blocks.update(blockId, {
                                    type: 'math',
                                    data: { content: mathElement.value }
                                });
                            });
                        } else {
                            console.warn('Block element does not have a data-id attribute.');
                        }
                    } else {
                        console.warn('Math-field is not inside a block element.');
                    }
    
                    // Replace the placeholder math-field with the initialized MathfieldElement
                    mathField.replaceWith(mathElement);
                }
            });
        }, 100);
    }
}