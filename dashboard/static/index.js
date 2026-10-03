document.addEventListener("DOMContentLoaded", function () {
  const container = document.getElementById("tile-container");
  const nested = document.getElementById("nested-container");
  const loader = document.getElementById("loader");
  const search = document.getElementById("search");
  const subfoldersButton = document.getElementById("search-subfolders");
  const message = document.getElementById("tile-message");
  const storageKey = "dashboard.searchSubfolders";
  let active = 0;
  let done = false;
  let failed = false;
  let nestedState = "idle";

  function setLoading(change) {
    active += change;
    loader.style.display = active > 0 ? '' : 'none';
  }

  function tiles(target) {
    return Array.from(target.children);
  }

  function visible(target) {
    return tiles(target).filter(tile => !tile.classList.contains('is-hidden'));
  }

  function query() {
    return search.value.trim().toLowerCase();
  }

  function subfolders() {
    return subfoldersButton !== null && subfoldersButton.getAttribute("aria-pressed") === "true";
  }

  function showNested() {
    return subfolders() && query() !== "";
  }

  function filter(tile) {
    const text = (tile.dataset.search || "").toLowerCase();
    tile.classList.toggle('is-hidden', !text.includes(query()));
  }

  function updateMessage() {
    const all = tiles(container);
    const searching = query() !== "";
    const nestedPending = showNested() && nestedState !== "done";
    let text = "";
    if (all.length === 0 && failed) {
      text = message.dataset.failed;
    } else if (all.length === 0 && done && !searching) {
      text = message.dataset.empty;
    } else if (searching && done && !nestedPending && visible(container).length === 0 &&
               (!showNested() || visible(nested).length === 0)) {
      text = message.dataset.noMatch;
    }
    message.textContent = text;
    message.classList.toggle('is-hidden', !text);
  }

  function insertTile(target, data) {
    const temp = document.createElement('template');
    temp.innerHTML = data.html;
    const newTile = temp.content.firstElementChild;
    newTile.dataset.index = data.id;
    newTile.classList.add('tile-wrapper');
    filter(newTile);

    const nextTile = tiles(target).find(tile =>
      parseInt(tile.dataset.index) > data.id
    );

    if (nextTile) {
      target.insertBefore(newTile, nextTile);
    } else {
      target.appendChild(newTile);
    }

    setTimeout(() => {
      newTile.classList.add('wrapper-visible');
    }, 20);
  }

  function stream(target, onEnd) {
    const eventSource = new EventSource(target.dataset.streamUrl);
    setLoading(1);

    function end(error) {
      eventSource.close();
      setLoading(-1);
      onEnd(error);
      updateMessage();
    }

    // Without this the browser reconnects on its own and every tile would be added twice
    eventSource.onerror = () => end(true);

    eventSource.onmessage = function (e) {
      const data = JSON.parse(e.data);
      if (data.done) {
        end(false);
        return;
      }
      insertTile(target, data);
      updateMessage();
    };
  }

  function applySearch() {
    tiles(container).forEach(filter);
    tiles(nested).forEach(filter);
    if (showNested() && nestedState === "idle") {
      nestedState = "loading";
      stream(nested, () => { nestedState = "done"; });
    }
    nested.classList.toggle('is-hidden', !showNested());
    updateMessage();
  }

  function setSubfolders(enabled) {
    subfoldersButton.setAttribute("aria-pressed", enabled ? "true" : "false");
    subfoldersButton.classList.toggle('is-info', enabled);
  }

  stream(container, error => {
    done = true;
    failed = error;
  });

  if (subfoldersButton) {
    try {
      setSubfolders(localStorage.getItem(storageKey) === "true");
    } catch (e) {
      setSubfolders(false);
    }
    subfoldersButton.addEventListener("click", function () {
      setSubfolders(!subfolders());
      try {
        localStorage.setItem(storageKey, subfolders() ? "true" : "false");
      } catch (e) {
        // Remembering the choice is optional
      }
      applySearch();
      search.focus();
    });
  }

  search.addEventListener("input", applySearch);

  search.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      const first = visible(container)[0] || (showNested() ? visible(nested)[0] : undefined);
      if (first) {
        first.querySelector("a.link").click();
      }
    } else if (e.key === "Escape") {
      search.value = "";
      applySearch();
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
