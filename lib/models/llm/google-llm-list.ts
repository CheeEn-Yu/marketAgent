import { LLM } from "@/types"

const GOOGLE_PLATORM_LINK = "https://ai.google.dev/"

// Google Models (UPDATED 12/22/23) -----------------------------

// Gemini 1.5 Flash
const GEMINI_1_5_FLASH: LLM = {
  modelId: "gemini-1.5-flash",
  modelName: "Gemini 1.5 Flash",
  provider: "google",
  hostedId: "gemini-1.5-flash",
  platformLink: GOOGLE_PLATORM_LINK,
  imageInput: true
}

// Gemini 1.5 Pro (UPDATED 05/28/24)
const GEMINI_1_5_PRO: LLM = {
  modelId: "gemini-1.5-pro",
  modelName: "Gemini 1.5 Pro",
  provider: "google",
  hostedId: "gemini-1.5-pro-latest",
  platformLink: GOOGLE_PLATORM_LINK,
  imageInput: true
}

// Gemini Pro Vision (UPDATED 12/22/23)
const GEMINI_2_0_FLASH: LLM = {
  modelId: "gemini-2.0-flash-001",
  modelName: "Gemini 2.0 Flash",
  provider: "google",
  hostedId: "gemini-pro-vision",
  platformLink: GOOGLE_PLATORM_LINK,
  imageInput: true
}

// Gemini Pro (UPDATED 12/22/23)
const GEMINI_2_0_PRO: LLM = {
  modelId: "gemini-2.0-pro-exp-02-05",
  modelName: "Gemini 2.0 Pro",
  provider: "google",
  hostedId: "gemini-pro",
  platformLink: GOOGLE_PLATORM_LINK,
  imageInput: false
}

export const GOOGLE_LLM_LIST: LLM[] = [
  GEMINI_1_5_PRO,
  GEMINI_1_5_FLASH,
  GEMINI_2_0_FLASH,
  GEMINI_2_0_PRO
]
