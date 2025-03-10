import { ChatSettings } from "@/types"
import { spawn } from "child_process"

export async function POST(request: Request) {
  const json = await request.json()
  const {
    chatSettings,
    messages,
    userRole,
    isSumMode,
    sumModeCompany,
    sumModeYear,
    sumModeQuarter
  } = json as {
    chatSettings: ChatSettings
    messages: any[]
    userRole: string
    isSumMode: boolean
    sumModeCompany: string
    sumModeYear: string
    sumModeQuarter: string
  }
  // console.log(json)
  try {
    const lastMessage = messages.pop()
    const prompt = lastMessage.parts // adjust if parts is not exactly a string
    // Execute Python script
    const messagesJson = JSON.stringify(messages)
    const pythonProcess = isSumMode ?
      spawn("python", [
        "python_backend/summarize.py",
        "--company",
        sumModeCompany,
        "--year",
        sumModeYear,
        "--quarter",
        sumModeQuarter,
      ])
      :
      spawn("python", [
        "python_backend/chat.py",
        "--prompt",
        prompt[0].text,
        "--history",
        messagesJson,
        "--user_role",
        userRole,
        "--is_sum_mode",
        isSumMode,
        "--sum_mode_company",
        sumModeCompany,
        "--sum_mode_year",
        sumModeYear,
        "--sum_mode_quarter",
        sumModeQuarter,
        "--temperature",
        chatSettings.temperature,
        "--max_tokens",
        chatSettings.contextLength,
        "--model_name",
        chatSettings.model
      ]) 
      

    let pythonData = ""

    pythonProcess.stdout.on("data", data => {
      pythonData += data.toString()
    })
    return new Promise((resolve, reject) => {
      pythonProcess.stderr.on("data", data => {
        console.error(`Python Error: ${data}`)
      })

      pythonProcess.on("close", code => {
        if (code !== 0) {
          reject(new Error(`Python process exited with code ${code}`))
          return
        }

        try {
          const encoder = new TextEncoder()
          // const readableStream = new ReadableStream({
          //   async start(controller) {
          //     for await (const item of pythonData) {
          //       const chunkText = item
          //       controller.enqueue(encoder.encode(chunkText))
          //       console.log(chunkText)
          //     }
          //     controller.close()
          //   }
          // })
          resolve(
            new Response(encoder.encode(pythonData), {
              headers: { "Content-Type": "application/json" }
            })
          )
        } catch (error) {
          reject(new Error("Failed to parse Python output"))
        }
      })
    })
  } catch (error: any) {
    let errorMessage = error.message || "An unexpected error occurred"
    const errorCode = error.status || 500

    return new Response(JSON.stringify({ message: errorMessage }), {
      status: errorCode,
      headers: { "Content-Type": "application/json" }
    })
  }
}
