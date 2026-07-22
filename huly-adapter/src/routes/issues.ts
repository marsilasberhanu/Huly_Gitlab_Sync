import { Router } from "express";
import { createIssue } from "../services/huly.service.js";
import { listIssues } from "../services/huly.list.service.js";

const router = Router();

router.get("/health", (_req, res) => {
  res.json({
    ok: true,
    service: "huly-adapter"
  });
});

router.get("/", async (req, res) => {
  try {
    const projectId = req.query.projectId as string | undefined;
    const limit = Number(req.query.limit ?? 20);

    const result = await listIssues(projectId, limit);

    res.json(result);
  } catch (err: any) {
    console.error(err);

    res.status(500).json({
      success: false,
      error: err.message ?? "Unknown error"
    });
  }
});

router.post("/", async (req, res) => {
  try {
    const result = await createIssue(req.body);

    res.status(201).json(result);
  } catch (err: any) {
    console.error(err);

    res.status(500).json({
      success: false,
      error: err.message ?? "Unknown error"
    });
  }
});

export default router;