{
  const userInputButton = document.querySelector("#userInputButton");
  const userInputElem = document.querySelector("#userInput");
  const ontologyText = document.querySelector("#ontology");
  const messages = document.querySelector("#messages");

  messages.scrollTop = messages.scrollHeight;

  /* register change in ontology so we know when to send it again */
  ontologyText.addEventListener("change", (event) => {
    ontologyText.setAttribute("data-changed", "true");
  });

  userInputButton.addEventListener('htmx:configRequest', function (evt) {
    if (ontologyText.getAttribute("data-changed") === "true") {
      // send ontology along with request if it changed
      evt.detail.parameters['ontology'] = ontologyText.value;
    }
    // reset input and disable button until we get a response or an error
    userInputElem.value = ''; // reset content
    userInputButton.disabled = true;
  });

  userInputButton.addEventListener('htmx:afterRequest', function (evt) {
    // enable button again after request is done
    userInputButton.disabled = false;
  });

  messages.addEventListener('htmx:afterSwap', function (evt) {
    messages.scrollTop = messages.scrollHeight;
  });
}
