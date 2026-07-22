import { Router } from "express";
import trackerRaw from "@hcengineering/tracker";
import { getHulyRestClient, closeClient } from "../services/huly.client.js";

const tracker = (trackerRaw as any).default ?? trackerRaw;

const router = Router();

router.get("/", async (_req, res) => {
  const client = await getHulyRestClient();

  try {
    const projects = await client.findAll(tracker.class.Project, {});

    res.json({
      success: true,
      count: projects.length,
      projects
    });
  } catch (err: any) {
    console.error(err);

    res.status(500).json({
      success: false,
      error: err.message ?? "Unknown error"
    });
  } finally {
    await closeClient(client);
  }
});

export default router;