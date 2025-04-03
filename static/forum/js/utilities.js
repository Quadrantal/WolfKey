


export function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
}