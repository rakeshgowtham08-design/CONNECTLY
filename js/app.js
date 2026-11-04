(() => {
  const csrfToken = (form) =>
    form.querySelector('input[name="csrfmiddlewaretoken"]')?.value || "";

  const showError = (message) => {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      stack.setAttribute("aria-live", "polite");
      document.body.append(stack);
    }
    const toast = document.createElement("div");
    toast.className = "toast toast-error";
    toast.textContent = message;
    stack.append(toast);
    window.setTimeout(() => toast.remove(), 4000);
  };

  const updateLike = (form, data) => {
    const button = form.querySelector("button");
    button.classList.toggle("liked", data.liked);
    button.setAttribute("aria-pressed", String(data.liked));
    button.querySelector("span:last-child").textContent = data.liked ? "Liked" : "Like";
    const count = form.closest(".post-card").querySelector("[data-like-count]");
    count.textContent = `${data.likes_count} like${data.likes_count === 1 ? "" : "s"}`;
  };

  const updateFollow = (form, data) => {
    const button = form.querySelector("button");
    if (!button) return;
    button.setAttribute("aria-pressed", String(data.following));
    if (button.classList.contains("follow-mini")) {
      button.textContent = data.following ? "✓" : "+";
      button.setAttribute(
        "aria-label",
        `${data.following ? "Following" : "Follow"} ${data.username}`
      );
    } else {
      button.textContent = data.following ? "Following" : "Follow";
      button.classList.toggle("button-primary", !data.following);
      button.classList.toggle("button-outline", data.following);
    }
    const count = document.querySelector("[data-followers-count]");
    if (count && form.action.includes(`/u/${data.username}/follow/`)) {
      count.textContent = data.followers_count;
    }
  };

  const appendComment = (form, data) => {
    const post = form.closest(".post-card");
    const row = document.createElement("div");
    row.className = "comment-row";
    row.id = `comment-${data.id}`;
    const username = document.createElement("a");
    username.className = "comment-user";
    username.href = `/u/${encodeURIComponent(data.username)}/`;
    username.textContent = data.author;
    const body = document.createElement("span");
    body.textContent = data.body;
    row.append(username, body);
    form.before(row);
    const count = post.querySelector(".post-stats a");
    count.textContent = `${data.comments_count} comment${data.comments_count === 1 ? "" : "s"}`;
    form.querySelector('input[name="body"]').value = "";
  };

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("form[data-ajax-form]");
    if (!form) return;
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    const previousDisabled = button?.disabled;
    if (button) button.disabled = true;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: {
          "X-CSRFToken": csrfToken(form),
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
        credentials: "same-origin",
      });
      const data = await response.json();
      if (!response.ok) {
        const message = Array.isArray(data.errors)
          ? data.errors.join(" ")
          : data.error || "That didn’t work. Please try again.";
        throw new Error(message);
      }
      if (form.dataset.action === "like") updateLike(form, data);
      if (form.dataset.action === "follow") updateFollow(form, data);
      if (form.dataset.action === "comment") appendComment(form, data);
    } catch (error) {
      showError(error.message || "We couldn’t connect. Please try again.");
    } finally {
      if (button) button.disabled = previousDisabled;
    }
  });

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("form[data-confirm]");
    if (form && !window.confirm(form.dataset.confirm)) event.preventDefault();
  });

  document.querySelectorAll("[data-image-preview-form] input[type=file]").forEach((input) => {
    input.addEventListener("change", () => {
      const preview = input.form.querySelector(".upload-preview");
      const file = input.files?.[0];
      if (!preview || !file) return;
      if (!file.type.startsWith("image/")) {
        showError("Choose an image file to preview.");
        input.value = "";
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        showError("Images must be 5 MB or smaller.");
        input.value = "";
        preview.hidden = true;
        return;
      }
      preview.src = URL.createObjectURL(file);
      preview.hidden = false;
    });
  });

  document.querySelectorAll(".toast").forEach((toast) => {
    window.setTimeout(() => toast.remove(), 4500);
  });
})();
