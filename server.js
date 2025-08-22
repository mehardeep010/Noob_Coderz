import express from "express";
import multer from "multer";
import cors from "cors";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import { spawn } from "child_process";
import dotenv from "dotenv";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(cors());
app.use(express.json());

// Ensure folders exist
const UPLOAD_DIR = path.join(__dirname, "uploads");
const OUTPUT_DIR = path.join(__dirname, "outputs");
for (const d of [UPLOAD_DIR, OUTPUT_DIR]) {
  if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
}

// Static frontend
app.use(express.static(path.join(__dirname, "public")));

// Multer storage
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, UPLOAD_DIR),
  filename: (req, file, cb) => {
    const ts = Date.now();
    const safe = file.originalname.replace(/[^a-zA-Z0-9_.-]/g, "_");
    cb(null, `${ts}_${safe}`);
  },
});
const upload = multer({ storage, limits: { fileSize: 50 * 1024 * 1024 } }); // 50MB

// Health
app.get("/api/health", (_req, res) => res.json({ ok: true }));

// Main route: upload PDF → Python → return funny PDF
app.post("/api/funnyify", upload.single("file"), (req, res) => {
  if (!req.file) return res.status(400).json({ error: "No file uploaded" });

  const inputPath = req.file.path;
  const outName = `${path.parse(req.file.filename).name}_funny.pdf`;
  const outputPath = path.join(OUTPUT_DIR, outName);

  const style = req.body.style || "mild"; // mild | spicy | chaotic
  const cats = req.body.cats === "false" ? "false" : "true"; // default true
  const emoji = req.body.emoji === "false" ? "false" : "true"; // default true
  const ai = req.body.ai || "none"; // none | openai
  const catEvery = req.body.catEvery || "4"; // insert cat every N paragraphs

  const py = spawn(process.env.PYTHON_BIN || "python3", [
    path.join(__dirname, "funnyify.py"),
    "--in", inputPath,
    "--out", outputPath,
    "--style", style,
    "--cats", cats,
    "--emoji", emoji,
    "--ai", ai,
    "--cat-every", catEvery,
  ], {
    env: { ...process.env },
  });

  let stderr = "";
  py.stderr.on("data", (d) => { stderr += d.toString(); });

  py.on("close", (code) => {
    // Clean up the upload regardless of success
    setTimeout(() => fs.unlink(inputPath, () => {}), 10_000);

    if (code !== 0) {
      console.error("Python failed:", stderr);
      return res.status(500).json({ error: "Processing failed", details: stderr });
    }

    // Stream the PDF as a download
    res.setHeader("Content-Type", "application/pdf");
    res.setHeader("Content-Disposition", `attachment; filename="${outName}"`);
    const stream = fs.createReadStream(outputPath);
    stream.pipe(res);
    stream.on("close", () => {
      // optional: delete output after sent
      setTimeout(() => fs.unlink(outputPath, () => {}), 60_000);
    });
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Chaotic PDF Reader running on http://localhost:${PORT}`));
