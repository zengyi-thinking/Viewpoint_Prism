export type * from './source'
export type * from './analysis'
export type * from './chat'
export type {
  DebateTask,
  DebateRequest,
  DebateStatusResponse,
  SupercutClip,
  SupercutTask,
  EntityStats,
  DigestTask,
  OnePagerData,
  EntityCardState,
} from './creative'
export type * from './ingest'
export type {
  Persona,
  PersonaConfig,
  StoryboardFrame,
  DirectorTask,
  DirectorRequest,
  DirectorStatusResponse,
} from './director'
export type * from './nebula'
export type * from './story'

export type PanelPosition = 'left' | 'bottom' | 'right'
export type AnalysisTab = 'conflicts' | 'graph' | 'timeline'
export type Language = 'zh' | 'en'
export type ActivePlayer = 'main' | 'debate' | 'supercut' | 'digest' | 'director' | 'nebula' | null
