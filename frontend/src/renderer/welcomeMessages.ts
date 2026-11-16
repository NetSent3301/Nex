export interface WelcomeEntry {
  message: string;
  subtitle: string;
}

export const WELCOME_MESSAGES: readonly WelcomeEntry[] = [
  { message: "¿Qué vamos a construir hoy?", subtitle: "Describe tu idea y empezaremos" },
  { message: "Listo para programar", subtitle: "El entorno está preparado para ti" },
  { message: "Describe tu idea", subtitle: "Cuéntame qué necesitas crear" },
  { message: "Todo listo para compilar", subtitle: "Esperando tus instrucciones" },
  { message: "Esperando instrucciones", subtitle: "Sesión de desarrollo iniciada" },
  { message: "El entorno está preparado", subtitle: "Sistema operativo listo" },
  { message: "Abramos un proyecto", subtitle: "Elige lo que quieres construir" },
  { message: "Hora de escribir código", subtitle: "Teclea una orden para comenzar" },
  { message: "Construyamos algo útil", subtitle: "¿Qué problema resolvemos hoy?" },
  { message: "¿Qué problema resolvemos hoy?", subtitle: "Analizando el contexto" },
  { message: "Preparando el espacio de trabajo", subtitle: "Carga de módulos completa" },
  { message: "Sesión de desarrollo iniciada", subtitle: "Terminal en espera" },
  { message: "Sistema operativo listo", subtitle: "Ciclo de trabajo listo" },
  { message: "Carga de módulos completa", subtitle: "Entorno de desarrollo activo" },
  { message: "Terminal en espera", subtitle: "Procesando directivas" },
  { message: "Todo en orden", subtitle: "Esperando tu próxima instrucción" },
  { message: "Analizando el contexto", subtitle: "Árbol de directorios sincronizado" },
  { message: "Ciclo de trabajo listo", subtitle: "Variables de entorno listas" },
  { message: "Entorno de desarrollo activo", subtitle: "Historial de cambios disponible" },
  { message: "Rendimiento del sistema óptimo", subtitle: "Listo para lo que necesites" },
  { message: "Esperando tu próxima instrucción", subtitle: "¿Cuál es el siguiente paso?" },
];

export function getRandomWelcomeMessage(): WelcomeEntry {
  const index = Math.floor(Math.random() * WELCOME_MESSAGES.length);
  return WELCOME_MESSAGES[index];
}
