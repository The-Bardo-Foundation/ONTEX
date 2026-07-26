import { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

const EditModeContext = createContext<{
  isEditMode: boolean;
  setIsEditMode: (v: boolean) => void;
}>({ isEditMode: false, setIsEditMode: () => {} });

export function EditModeProvider({ children }: { children: ReactNode }) {
  const [isEditMode, setIsEditMode] = useState(false);
  return (
    <EditModeContext.Provider value={{ isEditMode, setIsEditMode }}>
      {children}
    </EditModeContext.Provider>
  );
}

export function useEditMode() {
  return useContext(EditModeContext);
}
