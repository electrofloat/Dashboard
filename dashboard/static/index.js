document.addEventListener("DOMContentLoaded", function () {
  const container = document.getElementById("tile-container");
  const loader = document.getElementById("loader");
  const eventSource = new EventSource(container.dataset.streamUrl);
  loader.style.display = '';

  eventSource.onmessage = function (e) {
    const data = JSON.parse(e.data);

    if (data.done) {
      eventSource.close();
      loader.style.display = 'none';
      return;
    }

    const temp = document.createElement('template');
    temp.innerHTML = data.html;
    const newTile = temp.content.firstElementChild;
    newTile.dataset.index = data.id;
    newTile.classList.add('tile-wrapper');

    const existingTiles = Array.from(container.children);
    const nextTile = existingTiles.find(tile =>
      parseInt(tile.dataset.index) > data.id
    );

    if (nextTile) {
      container.insertBefore(newTile, nextTile);
    } else {
      container.appendChild(newTile);
    }

    setTimeout(() => {
      newTile.classList.add('wrapper-visible');
    }, 20);
  };
});
