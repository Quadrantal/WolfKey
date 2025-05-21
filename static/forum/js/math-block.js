export class MathLiveBlock {
    constructor({ data, config, api, readOnly }) {
      this.api = api;
      this.data = data || { content: "" };
      this.wrapper = null;
      this.readOnly = readOnly
    }
  
    static get toolbox() {
      return {
        title: "Math",
        icon: "∑",
      };
    }
  
    render() {
      this.wrapper = document.createElement("div");
      this.wrapper.contentEditable = false;
  
      // Create MathLive math field
      const mathField = document.createElement("math-field");
      mathField.setAttribute("style", "min-width: 100px; min-height: 30px;");
      mathField.value = this.data.content;


      mathField.addEventListener('keydown', (event) => {
        if(event.key === 'ArrowRight' || event.key === 'ArrowLeft'){
        event.preventDefault();
        event.stopPropagation();

        mathField.focus();
        }

        if(event.key === "/"|| event.code === "Slash"){
            event.stopPropagation();
            event.preventDefault();
    
            mathField.focus();
          }


        console.log("Event: ", event);

        if (event.code == "Backspace" || event.code == "Delete") {
          console.log("Delete/Backspace pressed");
          event.stopImmediatePropagation();
          event.stopPropagation();
          event.preventDefault();

          mathField.focus();
        }

        if (event.code == "Enter") {
          event.stopImmediatePropagation();
          event.stopPropagation();
          event.preventDefault();

          mathField.focus();
        }
      });
  
      // Event listener to save changes
      mathField.addEventListener("input", () => {
        this.data.content = mathField.value;
        console.log(this.data.content);
        this.save();
      });
  
      this.wrapper.appendChild(mathField);

        return this.wrapper;
    }
  
    save() {
        console.log("[MathLiveBlock] Saving block with content:", this.data.content);
      return {
        content: this.data.content || "",
      };
    }

    validate(savedData) {
        console.log("[MathLiveBlock] Validating block data:", savedData);
        return savedData.content !== undefined;
      }


  static get isReadOnlySupported() {
    return true;
  }
  }
  
