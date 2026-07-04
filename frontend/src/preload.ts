import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("netosAPI", {
  sendMessage: (message: string): Promise<{ success: boolean; response: string }> => {
    return ipcRenderer.invoke("send-to-backend", message);
  },
});
