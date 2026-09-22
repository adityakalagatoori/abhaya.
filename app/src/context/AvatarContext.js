import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { DEFAULT_AVATAR } from "../components/avatar/avatarOptions";

const STORAGE_KEY = "abhaya.avatarConfig.v1";
const AvatarContext = createContext(null);

export function AvatarProvider({ children }) {
  const [avatar, setAvatarState] = useState(DEFAULT_AVATAR);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (raw) setAvatarState({ ...DEFAULT_AVATAR, ...JSON.parse(raw) });
      } catch (e) {
        // ignore corrupt storage, fall back to default
      } finally {
        setLoaded(true);
      }
    })();
  }, []);

  const updateAvatar = useCallback((patch) => {
    setAvatarState((prev) => {
      const next = { ...prev, ...patch };
      AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
  }, []);

  return (
    <AvatarContext.Provider value={{ avatar, updateAvatar, loaded }}>
      {children}
    </AvatarContext.Provider>
  );
}

export function useAvatar() {
  const ctx = useContext(AvatarContext);
  if (!ctx) throw new Error("useAvatar must be used within AvatarProvider");
  return ctx;
}
