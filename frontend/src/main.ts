import { app, BrowserWindow, ipcMain } from "electron";

app.whenReady().then(() => {
  const win = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: "#080809",
    webPreferences: {
      preload: __dirname + "/preload.js",
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadFile(__dirname + "/index.html");
});

ipcMain.handle(
  "send-to-backend",
  async (_event, message: string): Promise<{ success: boolean; response: string }> => {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    return {
      success: true,
      response: "Respuesta simulada de Gemini para: " + message,
    };
  }
);
