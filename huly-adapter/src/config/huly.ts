import dotenv from "dotenv";

dotenv.config();

export const config = {

    url: process.env.HULY_URL!,

    token: process.env.HULY_TOKEN!,

    workspace: process.env.HULY_WORKSPACE_ID!,

    project: process.env.HULY_PROJECT_ID!

};