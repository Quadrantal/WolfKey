const createEditor = (holder,initialData, csrfToken, isReadOnly = false) => {
    return new EditorJS({
        holder: 'editorjs',  // The container where Editor.js will be initialized
        data: initialData,
        readOnly: isReadOnly,
        tools: {
            image: {
                class: ImageTool,
                config: {
                    endpoints: {
                        byFile: '/upload-image/', // URL to upload files
                    },
                    field: 'image', // The name of the field expected by the backend
                    additionalRequestHeaders: {
                        'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value
                    }
                }
            },
            header: {
                class: Header,
                shortcut: 'CMD+SHIFT+H',
                levels: [1,2, 3, 4],
                defaultLevel: 2
            },
            quote: {
                class: Quote,
                inlineToolbar: true,
                shortcut: 'CMD+SHIFT+O',
                config: {
                    quotePlaceholder: 'Enter a quote',
                    captionPlaceholder: 'Quote\'s author',
                },
            },
            delimiter: {
                class: Delimiter,
                config: {
                    styleOptions: ['star', 'dash', 'line'],
                    defaultStyle: 'line',
                    lineWidthOptions: [8, 15, 25, 35, 50, 60, 100],
                    defaultLineWidth: 25,
                    lineThicknessOptions: [1, 2, 3, 4, 5, 6],
                    defaultLineThickness: 2,
                }
            },
            list: {
                class: EditorjsList,
                inlineToolbar: true,
                config: {
                    defaultStyle: 'unordered'
                },
            },
            Math: {
                class: EJLaTeX,
            },
            code: editorJsCodeCup,
            inlineCode: {
                class: InlineCode,
            },
            inlineMath: InlineMath,
        },
        onReady: () => {
            console.log('Editor.js is ready!');
            document.querySelectorAll('.inline-math').forEach(elem => {
            const tex = elem.getAttribute('data-tex');
            if (tex) {
                const mathField = new MathfieldElement();
                mathField.value = tex;
                if (isReadOnly) {
                    mathField.setAttribute('read-only', '');
                }
                elem.appendChild(mathField);
            }
        });
        },
        onChange: !isReadOnly ? (api) => {
            api.saver.save()
                .then((outputData) => {
                    document.getElementById('editorjs-content').value = JSON.stringify(outputData);
                    console.log("Editor.js content saved");
                })
                .catch((error) => {
                    console.error('Saving failed: ', error);
                });
        } : undefined,
        minHeight: 75,
    })
}

