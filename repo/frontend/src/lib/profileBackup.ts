const PROFILE_BACKUP_PREFIX = 'meritforge.localExportBackup.v1'

export function getProfileBackupKey(userId: string): string {
  return `${PROFILE_BACKUP_PREFIX}.${userId}`
}
