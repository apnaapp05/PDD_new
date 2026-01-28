import { GoogleGenAI } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export const generateClinicalSummary = async (patientHistory: string): Promise<string> => {
  try {
    if (!process.env.API_KEY) {
        return "AI Service Unavailable: Missing API Key.";
    }

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: `You are a medical assistant. Summarize the following patient dental history into a concise paragraph for a doctor's quick review. Highlight any major procedures or recurring issues.
      
      History:
      ${patientHistory}`,
    });

    return response.text || "Could not generate summary.";
  } catch (error) {
    console.error("Gemini API Error:", error);
    return "Error connecting to AI service.";
  }
};

export const chatWithReceptionist = async (message: string, history: {role: string, parts: {text: string}[]}[]): Promise<string> => {
    try {
        if (!process.env.API_KEY) {
            return "I'm sorry, I cannot process your request right now (Missing API Key).";
        }

        const chat = ai.chats.create({
            model: 'gemini-2.5-flash',
            history: history,
            config: {
                systemInstruction: "You are a helpful and polite dental clinic receptionist. Your goal is to help the patient book an appointment. Ask for their preferred date, time, and if they have a specific doctor in mind. Keep responses concise and friendly. Do not actually book the appointment, just simulate the conversation.",
            }
        });

        const result = await chat.sendMessage({ message });
        return result.text || "I didn't understand that.";

    } catch (error) {
        console.error("Gemini Chat Error:", error);
        return "I am having trouble connecting to the server.";
    }
};