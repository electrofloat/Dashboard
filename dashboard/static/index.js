document.addEventListener("DOMContentLoaded", function () {
  const container = document.getElementById("tile-container");
  const loader = document.getElementById("loader");
  const search = document.getElementById("search");
  const message = document.getElementById("tile-message");
  const eventSource = new EventSource(container.dataset.streamUrl);
  let done = false;
  let failed = false;
  loader.style.display = '';

  function stop() {
    eventSource.close();
    loader.style.display = 'none';
  }

  function tiles() {
    return Array.from(container.children);
  }

  function query() {
    return search.value.trim().toLowerCase();
  }

  function filter(tile) {
    const text = (tile.dataset.search || "").toLowerCase();
    tile.classList.toggle('is-hidden', !text.includes(query()));
  }

  function updateMessage() {
    const all = tiles();
    let text = "";
    if (all.length === 0 && failed) {
      text = message.dataset.failed;
    } else if (all.length === 0 && done) {
      text = message.dataset.empty;
    } else if (all.length > 0 && all.every(tile => tile.classList.contains('is-hidden'))) {
      text = message.dataset.noMatch;
    }
    message.textContent = text;
    message.classList.toggle('is-hidden', !text);
  }

  // Without this the browser reconnects on its own and every tile would be added twice
  eventSource.onerror = function () {
    failed = true;
    stop();
    updateMessage();
  };

  eventSource.onmessage = function (e) {
    const data = JSON.parse(e.data);

    if (data.done) {
      done = true;
      stop();
      updateMessage();
      return;
    }

    const temp = document.createElement('template');
    temp.innerHTML = data.html;
    const newTile = temp.content.firstElementChild;
    newTile.dataset.index = data.id;
    newTile.classList.add('tile-wrapper');
    filter(newTile);

    const nextTile = tiles().find(tile =>
      parseInt(tile.dataset.index) > data.id
    );

    if (nextTile) {
      container.insertBefore(newTile, nextTile);
    } else {
      container.appendChild(newTile);
    }
    updateMessage();

    setTimeout(() => {
      newTile.classList.add('wrapper-visible');
    }, 20);
  };

  search.addEventListener("input", function () {
    tiles().forEach(filter);
    updateMessage();
  });

  search.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      const first = tiles().find(tile => !tile.classList.contains('is-hidden'));
      if (first) {
        first.querySelector("a.link").click();
      }
    } else if (e.key === "Escape") {
      search.value = "";
      search.dispatchEvent(new Event("input"));
    }
  });

  document.addEventListener("keydown", function (e) {
    const typing = ["INPUT", "TEXTAREA"].includes(document.activeElement.tagName);
    if (e.key === "/" && !typing) {
      e.preventDefault();
      search.focus();
    }
  });
});
