import { Router } from "express";
import taskRaw from "@hcengineering/task";
import { getHulyRestClient, closeClient } from "../services/huly.client";

const task = (taskRaw as any).default ?? taskRaw;

const router = Router();

router.get("/issue-types", async (_req, res) => {
  const client = await getHulyRestClient();

  try {
    const types = await client.findAll(task.class.TaskType, {});

    res.json({
      success: true,
      count: types.length,
      types
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