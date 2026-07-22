import express from "express";
import issueRoutes from "./routes/issues.js";
import projectRoutes from "./routes/projects.js";
import metadataRoutes from "./routes/metadata.js";

const app = express();

app.use(express.json());

app.get("/debug/env", (_req, res) => {
  res.json({
    HULY_URL: process.env.HULY_URL,
    HULY_WORKSPACE_ID: process.env.HULY_WORKSPACE_ID,
    HULY_PROJECT_ID: process.env.HULY_PROJECT_ID,
    HAS_HULY_TOKEN: Boolean(process.env.HULY_TOKEN)
  });
});

app.use("/issues", issueRoutes);
app.use("/projects", projectRoutes);
app.use("/metadata", metadataRoutes);

export default app;