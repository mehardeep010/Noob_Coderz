const form = document.getElementById("uploadForm");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const preview = document.getElementById("preview");
const download = document.getElementById("download");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  statusEl.textContent = "Processing… this can take a few seconds for large PDFs.";
  resultEl.classList.add("hidden");

  const file = document.getElementById("file").files[0];
  const style = document.getElementById("style").value;
  const cats = document.getElementById("cats").checked;
  const emoji = document.getElementById("emoji").checked;
  const useAI = document.getElementById("useAI").checked;
  const catEvery = document.getElementById("catEvery").value || 4;

  const fd = new FormData();
  fd.append("file", file);
  fd.append("style", style);
  fd.append("cats", String(cats));
  fd.append("emoji", String(emoji));
  fd.append("ai", useAI ? "openai" : "none");
  fd.append("catEvery", String(catEvery));

  try {
    const res = await fetch("/api/funnyify", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || "Server error");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    preview.src = url;
    download.href = url;
    statusEl.textContent = "Done!";
    resultEl.classList.remove("hidden");
  } catch (e) {
    console.error(e);
    statusEl.textContent = "Failed: " + e.message;
  }
});
