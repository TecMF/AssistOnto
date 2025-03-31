{ //

  function disableButtonWhileRequestInFlight(button) {
    button.addEventListener('htmx:configRequest', function (_) {
      button.disabled = true;
    });
    button.addEventListener('htmx:afterRequest', function (_) {
      // enable button again after request is done
      button.disabled = false;
    });
  };

  const userInputButton = document.querySelector("#userInputButton");
  const reasonerButton = document.querySelector("#reasonerButton");
  const userInputElem = document.querySelector("#userInput");
  const ontologyText = document.querySelector("#ontology");
  const messages = document.querySelector("#messages");

  // disable buttons until answer comes
  disableButtonWhileRequestInFlight(userInputButton);
  disableButtonWhileRequestInFlight(reasonerButton);

  messages.scrollTop = messages.scrollHeight;

  /* register change in ontology so we know when to send it again */
  ontologyText.addEventListener("change", (_) => {
    ontologyText.setAttribute("data-changed", "true");
  });

  userInputButton.addEventListener('htmx:configRequest', function (evt) {
    if (ontologyText.getAttribute("data-changed") === "true") {
      // send ontology along with request if it changed
      evt.detail.parameters['user-ontology'] = ontologyText.value;
    }
    // reset input
    userInputElem.value = ''; // reset content
  });

  // scroll automatically after message arrives
  messages.addEventListener('htmx:afterSwap', function (_) {
    messages.scrollTop = messages.scrollHeight;
  });

}
