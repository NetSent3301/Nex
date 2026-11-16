export type Locale = "es" | "en" | "fr" | "pt" | "de";

export interface WelcomeEntry {
  message: string;
  subtitle: string;
}

export interface LocaleStrings {
  locale: Locale;
  label: string;
  common: {
    appName: string;
    newSession: string;
    settings: string;
    close: string;
    save: string;
    cancel: string;
    delete: string;
    rename: string;
    search: string;
    noResults: string;
    confirm: string;
    success: string;
    error: string;
  };
  sidebar: {
    today: string;
    yesterday: string;
    last7Days: string;
    older: string;
    noSessions: string;
    rename: string;
    delete: string;
    newSession: string;
    workspace: string;
  };
  chat: {
    you: string;
    nex: string;
    thinking: string;
    inputPlaceholder: string;
    copyResponse: string;
    copied: string;
    attachFile: string;
    stopExecution: string;
    sendMessage: string;
    errorPrefix: string;
    errorConnecting: string;
  };
  tool: {
    running: string;
    done: string;
    error: string;
  };
  welcome: {
    promptLine: string;
    quickActions: {
      writeCommand: string;
      writeCommandHint: string;
      exploreCode: string;
      exploreCodeHint: string;
      diagnose: string;
      diagnoseHint: string;
      settings: string;
      settingsHint: string;
    };
    entries: WelcomeEntry[];
  };
  settings: {
    title: string;
    subtitle: string;
    general: string;
    chat: string;
    provider: string;
    keys: string;
    system: string;
    data: string;
    appearance: string;
    generalTab: {
      theme: string;
      themeDark: string;
      themeLight: string;
      themeSystem: string;
      language: string;
      fontSize: string;
      curvature: string;
      animations: string;
      compactMode: string;
      compactModeDesc: string;
      orbAnimation: string;
      orbAnimationDesc: string;
      accentColor: string;
      fontFamily: string;
      sidebarVisible: string;
      resetAppearance: string;
    };
    chatTab: {
      behavior: string;
      temperature: string;
      topP: string;
      maxTokens: string;
      sendWith: string;
      enter: string;
      ctrlEnter: string;
      shiftEnter: string;
      autoScroll: string;
      timestamps: string;
      syntaxHighlighting: string;
      autoTitle: string;
      confirmDelete: string;
    };
    providerTab: {
      title: string;
      provider: string;
      model: string;
      loading: string;
      refreshModels: string;
      customUrls: string;
      openaiUrl: string;
      ollamaUrl: string;
      timeout: string;
      timeoutDesc: string;
    };
    keysTab: {
      title: string;
      desc: string;
      save: string;
      saved: string;
    };
    systemTab: {
      title: string;
      desc: string;
      systemPrompt: string;
      limits: string;
      maxToolCalls: string;
      autoSave: string;
      autoSaveDesc: string;
      maxSessions: string;
      maxSessionsDesc: string;
      contextSize: string;
      contextSizeDesc: string;
    };
    dataTab: {
      title: string;
      desc: string;
      export: string;
      import: string;
      clearHistory: string;
      clearHistoryConfirm: string;
      resetSettings: string;
      resetSettingsConfirm: string;
    };
  };
  metrics: {
    label: string;
    memory: string;
    contextBuffer: string;
    agentCore: string;
    online: string;
    busy: string;
    offline: string;
  };
  spotlight: {
    placeholder: string;
    create: string;
    msgs: string;
  };
  fileAttach: {
    dropImage: string;
    files: string;
  };
}

export type TranslationKey = string;
