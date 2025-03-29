/**
 * InlineMath - Editor.js inline tool for mathematical equations
 * Allows inserting and editing LaTeX equations within text
 * @class
 */
window.InlineMath = class InlineMath {
  /**
   * Initialize the inline math tool
   * @param {Object} param0 - Editor.js API object
   * @param {Object} param0.api - Editor.js API methods and properties
   */
  constructor({ api }) {
    // Core properties
    this.api = api;
    this.state = false; //Text in math notation or no. true: inside math span; false: plain text
    this.isProcessing = false;

    // DOM element references
    this.button = null;
    this.container = null;
    this.inlineMathTextInput = null;
    this.inlineMathNode = null;

    // Configuration
    this.inlineMathTag = "SPAN";
    this.inlineMathTagClass = "inline-math";
    this.texAttribute = "data-tex";
    this.initializeDelay = 100;

    // State tracking
    this.tex = "";
    this.isFocused = false;
    this.isActive = false; //Controls the visibility; true: Math input container is visible and accepting input false: Math input container is hidden
    this.lastActiveElement = null;
  }

  render() {
    // Create button
    this.button = document.createElement("button");
    this.button.classList.add(this.api.styles.inlineToolButton);
    this.button.type = "button";

    // Setup click handler with debounce
    this.button.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      console.log("🔘 Button clicked");
      this.lastActiveElement = document.activeElement;

      setTimeout(() => {
        this.isActive = true;
        this.isFocused = true;
        this.showActions();
        this.inlineMathTextInput?.focus();
      }, this.initializeDelay);
    });

    this.button.innerHTML = this._getButtonSVG();

    return this.button;
  }

  

  /**
   * Wrap selected text in math notation
   * @param {Range} range - The selected text range
   */
  wrap(range) {
    if (this.state) return;

    console.log("📝 Wrapping text in math notation");

    const selectedContent = range.extractContents();
    const tex = this._getNodeTextContent(selectedContent);
    const inlineMathNode = this._createMathNode(tex);

    if (this._findEditorBlock(range.startContainer)) {
      range.insertNode(inlineMathNode);
      this._updateState(true, inlineMathNode, tex);
    } else {
      console.warn("❌ Math insertion failed: Range outside editor");
    }

    this.state = true;
  }

  /**
 * Unwrap the math notation from the text
 * @param {Range} range - The selected text range
 */
  unwrap(range) {
    console.log("🔄 Unwrapping math notation");

    if (this.inlineMathNode) {
      this.inlineMathNode.remove();
      range.insertNode(document.createTextNode(this.tex));
    } else {
      const mark = this._findParentTag(range.startContainer);
      if (mark) mark.replaceWith(document.createTextNode(mark.textContent));
    }

    this.hideActions();
    this._updateState(false, null, "");
  }


  /**
 * Show the math input interface
 */
  showActions() {
    if (!this.isActive) return;

    if (!this.inlineMathTextInput) this.renderActions();
    if (this.inlineMathNode) this.inlineMathTextInput.value = this.tex;

    const selection = window.getSelection();
    if (!selection.rangeCount) return;

    const range = selection.getRangeAt(0);
    this.surround(range);

    if (!this.state) {
      this.unwrap(range);
      return;
    }

    this._positionContainer(range);
    this.inlineMathTextInput.value = this.tex || "";
    this.inlineMathTextInput.focus();
  }


  /**
   * Initialize the math input container and event handlers
   * Creates and configures the MathLive input field
   * @private
   */
  renderActions() {
    if (this.inlineMathTextInput) return;

    // Find EditorJS container
    const editorContainer = document.getElementById('editorjs');
    if (!editorContainer) {
      console.error("❌ EditorJS container not found");
      return;
    }

    // Create and setup container
    this.container = document.createElement('div');
    this.container.classList.add('inline-math-floating-container');

    // Create MathLive input
    this.inlineMathTextInput = new MathfieldElement();
    this.inlineMathTextInput.setAttribute('id', 'math-editor');

    // DOM setup
    this.container.appendChild(this.inlineMathTextInput);
    editorContainer.appendChild(this.container);

    // Add styles
    this.addStyles();

    // Setup MathLive configuration
    this.setupMathInput();
  }

  /**
 * Hide the math input interface
 * Updates math node content and hides container
 * @public
 */
  hideActions() {
    if (!this.isActive) return;

    if (this.inlineMathTextInput) {
      this.tex = this.inlineMathTextInput.value;
      console.log("✅ Tex updated:", this.tex);

      this._updateMathField(this.tex);
    }

    this.container.style.display = 'none';
    this.isActive = false;
  }

  surround(range) {
    console.log("🎯 Surround called, state:", this.state);
    this.state ? this.unwrap(range) : this.wrap(range);
  }

  checkState(selection) {
    if (this.isProcessing) return;

    console.log("🔍 Checking state...");
    this.inlineMathNode = this._findMathParent();
    this._updateStateFromNode();
  }

  /**
   * Create math node with embedded MathField
   * @private
   * @param {string} tex - LaTeX content
   * @param {DocumentFragment} content - Original content
   * @returns {HTMLElement} Configured math node
   */
  _createMathNode(tex, content) {
    // Create container span
    const node = document.createElement(this.inlineMathTag);
    node.classList.add(this.inlineMathTagClass);
    node.setAttribute(this.texAttribute, tex);

    // Create static MathField for display
    const mathField = new MathfieldElement();
    mathField.style.display = 'inline-block';
    mathField.style.minWidth = '1em';
    mathField.style.margin = '0 2px';
    mathField.style.padding = '0 2px';
    mathField.style.border = 'none';
    mathField.style.background = 'transparent';
    mathField.value = tex;

    // Add MathField to container
    node.appendChild(mathField);
    node.style.marginLeft = '5px';
    node.style.marginRight = '5px';
    node.mf = mathField;

    // Add a zero-width space before and after the mathfield to prevent empty paragraph
    const afterSpace = document.createTextNode('\u200B');
    node.appendChild(afterSpace);
    
    setTimeout(() => {
      const paragraph = node.closest('.ce-paragraph');
      if (paragraph) {
        paragraph.addEventListener('keydown', (event) => {
          if ((event.keyCode === 8 || event.keyCode === 46) && 
              document.activeElement !== node.mf) {
            // Allow deletion if we're not focused on the mathfield
            return true;
          }
        });
      }
    }, 0);

    
    node.mf.addEventListener('keydown', (event) => {
      const pos = node.mf.position;
      const length = node.mf.value.length;
      console.log(`🔹 Key: ${event.key}, Pos: ${pos}, Length: ${length}`);

      if(event.key === 'ArrowRight' || event.key === 'ArrowLeft'){
        event.preventDefault();
        event.stopPropagation();

        node.mf.focus();
      }

      if(event.key === "/"|| event.code === "Slash"){
        event.preventDefault();
        event.stopPropagation();

        node.mf.focus();
      }

      if (event.keyCode == 8 || event.keyCode == 46) {
        console.log("Delete/Backspace pressed");
        event.stopImmediatePropagation();
        event.stopPropagation();
        event.preventDefault();
        
        node.mf.focus();
      }
    });

    node.mf.addEventListener("focusin", () =>  mathVirtualKeyboard.show());
    node.mf.addEventListener("focusout", () =>  mathVirtualKeyboard.hide()); 
      
    return node;
  }

  _findEditorBlock(container) {
    if (container.nodeType === Node.TEXT_NODE) {
      return container.parentNode.closest('.ce-paragraph');
    }
    return container.closest('.ce-paragraph');
  }

  _updateState(state, node, tex) {
    this.state = state;
    this.inlineMathNode = node;
    this.tex = tex;
    console.log("✅ State updated:", { state, node, tex });
  }


  _unwrapExistingNode(range) {
    console.log("Unwrapping existing node");
    this.inlineMathNode.remove();
    const textNode = document.createTextNode(this.tex);
    range.insertNode(textNode);
  }

  _unwrapFoundNode(range) {
    console.log("Finding and unwrapping node");
    const mark = this._findParentTag(
      range.startContainer,
      this.inlineMathTag,
      this.inlineMathTagClass
    );
    const text = range.extractContents();
    if (mark) {
      mark.remove();
    }
    range.insertNode(text);
  }

  _findMathParent() {
    return this.api.selection.findParentTag(
      this.inlineMathTag,
      this.inlineMathTagClass
    );
  }

  _updateStateFromNode() {
    if (this.inlineMathNode) {
      this.state = true;
      this.tex = this.inlineMathNode.getAttribute(this.texAttribute) || '';
      console.log("✅ Found node:", { node: this.inlineMathNode, tex: this.tex });
    } else {
      this.state = false;
      this.tex = '';
      console.log("ℹ️ No node found");
    }
  }

  _positionContainer(range) {
    const rect = range.getBoundingClientRect();
    const editorRect = document.getElementById("editorjs").getBoundingClientRect();

    this.container.style.top = `${rect.top - editorRect.top - this.container.offsetHeight - 5}px`;
    this.container.style.left = `${rect.left - editorRect.left}px`;
    this.container.style.display = "block";
  }

  /**
   * Find parent element matching tag and class
   * @param {Node} node - Starting node to search from
   * @param {string} tagName - HTML tag to match
   * @param {string} className - CSS class to match
   * @returns {Element|null} Matching parent element or null
   */
  _findParentTag(node, tagName, className) {
    while (node && node !== document) {
      if (node.tagName === tagName && node.classList.contains(className)) {
        return node;
      }
      node = node.parentNode;
    }
    return null;
  }


  /**
   * Add required CSS styles to document
   * Sets up styling for math input container
   * @private
   */
  addStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .inline-math-floating-container {
          position: absolute;
          z-index: 1000;
          background: white;
          border: 1px solid #ccc;
          border-radius: 4px;
          box-shadow: 0 3px 15px -3px rgba(13,20,33,.13);
          padding: 6px;
          display: none;
        }
        #editorjs {
          position: relative;
        }
      `;
    document.head.appendChild(style);
  }

  /**
   * Sets up MathLive input field with event listeners and virtual keyboard
   * Configures focus, blur, and keyboard events
   * @private
   */
  setupMathInput() {
    // Configure MathLive virtual keyboard
    this.inlineMathTextInput.mathVirtualKeyboardPolicy = "manual";

    console.log(this.inlineMathTextInput);

    this.inlineMathTextInput.addEventListener("focusin", () =>  mathVirtualKeyboard.show());
    this.inlineMathTextInput.addEventListener("focusout", () =>  mathVirtualKeyboard.hide());
    
    this.inlineMathTextInput.addEventListener('keydown', (event) => {
      this.inlineMathTextInput.focus();
      const pos = this.inlineMathTextInput.position;
      const length = this.inlineMathTextInput.value.length;
      console.log(`🔹 Key: ${event.key}, Pos: ${pos}, Length: ${length}`);

      if(event.key === 'ArrowRight' || event.key === 'ArrowLeft'){
        event.preventDefault();
        event.stopPropagation();
  
        if(event.key === "ArrowRight"){
          this.inlineMathTextInput.executeCommand("moveToNextChar"); //Different than the one in the create new node bc idk
        }
  
        this.inlineMathTextInput.focus();
      }

      if(event.key === "/"|| event.code === "Slash"){
        event.stopPropagation();
        event.preventDefault();

        this.inlineMathTextInput.focus();
      }


    });

    // Prevent focusout event if caused by arrow key movement
    this.inlineMathTextInput.addEventListener('focusout', (event) => {
      event.preventDefault();
      // Check if the related target (new focused element) is still within the mathfield
      setTimeout(() => {
        if (document.activeElement === this.inlineMathTextInput) {
          return; // Do nothing if it's still focused
        }

        console.log("🖱️ Node Mathfield lost focus");
        this.hideActions();
      }, 0);
    });

  }

  /**
   * Update the math node with new tex value
   * @private
   * @param {string} tex - LaTeX content to set
   */
  _updateMathField(tex) {
    if (!this.inlineMathNode) {
      console.warn("⚠️ No math node to update");
      return;
    }

    console.log("✅ Updating math field with tex:", tex);
    this.inlineMathNode.mf.setValue(tex);
    this.inlineMathNode.setAttribute(this.texAttribute, tex);
  }

  /**
   * Extract text content from DOM node
   * Handles different node types (text, fragment, element)
   * @private
   * @param {Node} node - DOM node to extract text from
   * @returns {string} Plain text content
   */
  _getNodeTextContent(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent;
    }

    if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE ||
      node.nodeType === Node.ELEMENT_NODE) {
      let text = '';
      node.childNodes.forEach(child => {
        text += this._getNodeTextContent(child);
      });
      return text;
    }

    return '';
  }

  _getButtonSVG() {
    return `
    <svg width="800px" height="800px" viewBox="0 0 24 24" fill="none" xmlnse="http://www.w3.org/2000/svg">
    <path d="M12.1873 4.14049C11.2229 3.41714 9.84236 4.0695 9.78883 5.27389L9.71211 7H12C12.5523 7 13 7.44772 13 8C13 8.55228 12.5523 9 12 9H9.62322L9.22988 17.8501C9.0996 20.7815 5.63681 22.261 3.42857 20.3287L3.34151 20.2526C2.92587 19.8889 2.88375 19.2571 3.24743 18.8415C3.61112 18.4259 4.24288x 18.3837 4.65852 18.7474L4.74558 18.8236C5.69197 19.6517 7.17602 19.0176 7.23186 17.7613L7.62125 9H6C5.44772 9 5 8.55228 5 8C5 7.44772 5.44772 7 6 7H7.71014L7.7908 5.18509C7.9157 2.37483 11.1369 0.852675 13.3873 2.54049L13.6p 2.69999C14.0418 3.03136 14.1314 3.65817 13.8 4.09999C13.4686 4.54182 12.8418 4.63136 12.4 4.29999L12.1873 4.14049Z" fill="#212121"/>
    <path d="M13.082 13.0462C13.3348 12.9071 13.6525 13.0103 13.7754 13.2714L14.5879 14.9979L11.2928 18.2929C10.9023 18.6834 10.9023 19.3166 11.2928 19.7071C11.6834 20.0977 12.3165 20.0977 12.707 19.7071L15.493 16.9212L16.2729 18.5786C16.9676 20.0548 18.8673 20.4808 20.1259 19.4425L20.6363 19.0214C21.0623 18.6699 21.1228 18.0397 20.7713 17.6136C20.4198 17.1876 19.7896 17.1272 19.3636 17.4787L18.8531 17.8998C18.6014 18.1074 18.2215 18.0222 18.0825 17.727L16.996 15.4182L19.707 12.7071C20.0976 12.3166 20.0976 11.6834 19.707 11.2929C19.3165 10.9024 18.6834 10.9024 18.2928 11.2929L16.0909 13.4948L15.585 12.4198C14.9708 11.1144 13.3822 10.5985 12.1182 11.2937L11.518 11.6238C11.0341 11.89 10.8576 12.498 11.1237 12.982C11.3899 13.4659 11.998 13.6424 12.4819 13.3762L13.082 13.0462Z" fill="#212121"/>
    </svg>
    `;
  }

  static get isInline() {
    return true;
  }
  static get title() {
    return "Inline Math";
  }

  static get sanitize() {
    return {
      span: function () {
        return true;
      },
    };
  }
}
