import { Router, type Request } from "express";

import type { HulyConnectionConfig } from "../services/huly.client.js";
import { listIssues } from "../services/huly.list.service.js";
import { createIssue } from "../services/huly.service.js";


const router = Router();


function getConnection(
  req: Request
): HulyConnectionConfig | undefined {
  const token = req.header("X-Huly-Token");
  const workspace = req.header("X-Huly-Workspace");
  const url = req.header("X-Huly-Url");

  const suppliedValues = [token, workspace, url].filter(Boolean);

  // No custom credentials supplied:
  // fall back to the adapter environment variables.
  if (suppliedValues.length === 0) {
    return undefined;
  }

  if (!token || !workspace || !url) {
    throw new Error(
      "X-Huly-Token, X-Huly-Workspace and X-Huly-Url " +
      "must all be supplied together"
    );
  }

  return {
    token,
    workspace,
    url,
  };
}


router.get("/health", (_req, res) => {
  res.json({
    ok: true,
    service: "huly-adapter",
  });
});


router.get("/", async (req, res) => {
  try {
    const projectId = req.query.projectId as string | undefined;
    const limit = Number(req.query.limit ?? 20);
    const connection = getConnection(req);

    const result = await listIssues(
      projectId,
      limit,
      connection
    );

    res.json(result);
  } catch (err: any) {
    console.error(err);

    res.status(500).json({
      success: false,
      error: err.message ?? "Unknown error",
    });
  }
});


router.post("/", async (req, res) => {
  try {
    const connection = getConnection(req);

    const result = await createIssue(
      req.body,
      connection
    );

    res.status(201).json(result);
  } catch (err: any) {
    console.error(err);

    res.status(500).json({
      success: false,
      error: err.message ?? "Unknown error",
    });
  }
});


export default router;
