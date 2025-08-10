// static/js/journal.js
// Handles CSRF and AJAX calls to update status and rating

function getCookie(name) {
  // standard Django cookie reader
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const c = cookies[i].trim();
      if (c.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(c.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
const csrftoken = getCookie('csrftoken');

async function postJSON(url, formData) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
    },
    body: formData
  });
  return resp.json();
}

/* ====== Status (watchlist/favorite/watched) ====== */
document.addEventListener('click', async (e) => {
  const toggleBtn = e.target.closest('[data-action="toggle-status"]');
  if (!toggleBtn) return;

  const tmdbId = toggleBtn.dataset.tmdbId;
  const desired = toggleBtn.dataset.status; // e.g. "favorite" or "watchlist" or "watched"
  const url = `/journal/status/${tmdbId}/`;

  const fd = new FormData();
  fd.append('status', desired);

  toggleBtn.classList.add('disabled');
  const json = await postJSON(url, fd);
  toggleBtn.classList.remove('disabled');

  if (json && json.ok) {
    // update UI states (toggle active class)
    const buttons = document.querySelectorAll(`[data-tmdb-id="${tmdbId}"][data-action="toggle-status"]`);
    buttons.forEach(btn => {
      if (btn.dataset.status === json.status) {
        btn.classList.add('btn-success');
        btn.classList.remove('btn-outline-light');
      } else {
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-light');
      }
    });
  } else {
    alert(json && json.error ? json.error : 'Failed to update status');
  }
});

/* ====== Rating (stars) ====== */
// star elements should have data-action="rate" and data-tmdb-id and data-value (1..5)
document.addEventListener('click', async (e) => {
  const star = e.target.closest('[data-action="rate"]');
  if (!star) return;

  const tmdbId = star.dataset.tmdbId;
  const starValue = Number(star.dataset.value); // 1..5
  // convert 1..5 star to 1..10 rating (2 * star)
  const rating = Math.min(10, Math.max(1, starValue * 2));

  const fd = new FormData();
  fd.append('rating', rating);

  const url = `/journal/rate/${tmdbId}/`;
  const json = await postJSON(url, fd);

  if (json && json.ok) {
    // update star UI for this tmdbId
    const starElems = document.querySelectorAll(`[data-action="rate"][data-tmdb-id="${tmdbId}"]`);
    starElems.forEach(el => {
      const v = Number(el.dataset.value);
      if (v <= Math.ceil(json.rating / 2)) {
        el.classList.add('rated');
      } else {
        el.classList.remove('rated');
      }
    });
  } else {
    alert(json && json.error ? json.error : 'Failed to set rating');
  }
});

// Initialize star visuals on page load for any .star-container elements
document.addEventListener('DOMContentLoaded', () => {
  const containers = document.querySelectorAll('.star-container');
  containers.forEach(container => {
    const rating = Number(container.dataset.rating || 0); // 1..10 scale expected
    // compute how many stars to fill (1..5) using ceil(rating / 2)
    const starsToFill = Math.ceil((rating || 0) / 2);
    const starElems = container.querySelectorAll('[data-action="rate"]');
    starElems.forEach(el => {
      const v = Number(el.dataset.value);
      if (v <= starsToFill && starsToFill > 0) {
        el.classList.add('rated');
      } else {
        el.classList.remove('rated');
      }
    });
  });
});


// static/js/journal.js
// Handles CSRF and AJAX calls to update status and rating
// Includes hover-fill star animations and tooltip init.

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const c = cookies[i].trim();
      if (c.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(c.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
// const csrftoken = getCookie('csrftoken');

async function postForm(url, formData) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrftoken },
    body: formData
  });
  return resp.json().catch(() => ({ ok: false, error: 'invalid json response' }));
}

function fillStars(container, count) {
  const stars = container.querySelectorAll('[data-action="rate"]');
  stars.forEach(el => {
    const v = Number(el.dataset.value);
    if (v <= count && count > 0) el.classList.add('rated');
    else el.classList.remove('rated');
  });
}

/* ====== Status (watchlist/favorite/watched) ====== */
document.addEventListener('click', async (e) => {
  const toggleBtn = e.target.closest('[data-action="toggle-status"]');
  if (!toggleBtn) return;

  const tmdbId = toggleBtn.dataset.tmdbId;
  const desired = toggleBtn.dataset.status;
  const url = `/journal/status/${tmdbId}/`;

  const fd = new FormData();
  fd.append('status', desired);

  toggleBtn.classList.add('disabled');
  const json = await postForm(url, fd);
  toggleBtn.classList.remove('disabled');

  if (json && json.ok) {
    // update UI states for all buttons for that tmdbId
    const buttons = document.querySelectorAll(`[data-tmdb-id="${tmdbId}"][data-action="toggle-status"]`);
    buttons.forEach(btn => {
      if (btn.dataset.status === json.status) {
        btn.classList.add('btn-success');
        btn.classList.remove('btn-outline-light');
        btn.setAttribute('aria-pressed', 'true');
      } else {
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-light');
        btn.setAttribute('aria-pressed', 'false');
      }
    });
  } else {
    alert(json && json.error ? json.error : 'Failed to update status');
  }
});

/* ====== Rating (stars) ====== */
// click to rate
document.addEventListener('click', async (e) => {
  const star = e.target.closest('[data-action="rate"]');
  if (!star) return;

  const tmdbId = star.dataset.tmdbId;
  const starValue = Number(star.dataset.value); // 1..5
  const rating = Math.min(10, Math.max(1, starValue * 2)); // convert to 1..10

  const fd = new FormData();
  fd.append('rating', rating);
  const url = `/journal/rate/${tmdbId}/`;

  const parent = document.querySelector(`.star-container[data-tmdb-id="${tmdbId}"]`);
  const oldFill = parent ? Number(parent.dataset.rating || 0) : 0;

  const json = await postForm(url, fd);
  if (json && json.ok) {
    // update displayed numeric rating (if present)
    const containers = document.querySelectorAll(`.star-container[data-tmdb-id="${tmdbId}"]`);
    containers.forEach(c => {
      c.dataset.rating = json.rating || 0;
      fillStars(c, Math.ceil((json.rating || 0) / 2));
    });
    // update small numeric text nearby (if any)
    const smalls = document.querySelectorAll(`.star-container[data-tmdb-id="${tmdbId}"] + .small, .star-container[data-tmdb-id="${tmdbId}"] ~ .small`);
    smalls.forEach(s => {
      s.textContent = (json.rating ? `${json.rating} / 10` : 'No rating');
    });
  } else {
    alert(json && json.error ? json.error : 'Failed to set rating');
  }
});

// hover behavior: fill up to hovered star; restore on mouseout
document.addEventListener('mouseover', (e) => {
  const star = e.target.closest('[data-action="rate"]');
  if (!star) return;
  const tmdbId = star.dataset.tmdbId;
  const val = Number(star.dataset.value);
  const container = document.querySelector(`.star-container[data-tmdb-id="${tmdbId}"]`);
  if (container) fillStars(container, val);
});

document.addEventListener('mouseout', (e) => {
  const left = e.target.closest('[data-action="rate"]');
  if (!left) return;
  const tmdbId = left.dataset.tmdbId;
  const container = document.querySelector(`.star-container[data-tmdb-id="${tmdbId}"]`);
  if (container) {
    const rating = Number(container.dataset.rating || 0);
    fillStars(container, Math.ceil(rating / 2));
  }
});

// initialize star visuals on DOM ready and set up bootstrap tooltips
document.addEventListener('DOMContentLoaded', () => {
  const containers = document.querySelectorAll('.star-container');
  containers.forEach(container => {
    const rating = Number(container.dataset.rating || 0);
    const starsToFill = Math.ceil((rating || 0) / 2);
    fillStars(container, starsToFill);
  });

  // bootstrap tooltip init (requires bootstrap.bundle.js)
  if (typeof bootstrap !== 'undefined') {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (el) {
      try { new bootstrap.Tooltip(el); } catch (err) { /* ignore */ }
    });
  }
});

