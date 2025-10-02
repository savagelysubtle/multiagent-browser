// Type definitions for the Electron desktop API
declare global {
  interface Window {
    desktop: {
      // App information
      getVersion(): Promise<string>;
      getPlatform(): Promise<string>;
      ping(): Promise<string>;

      // System information
      isElectron: boolean;

      // Future APIs can be typed here following the same pattern
      // Example:
      // fileSystem: {
      //   readFile(path: string): Promise<string>;
      //   writeFile(path: string, data: string): Promise<void>;
      // }
    };
  }
}

export { };
