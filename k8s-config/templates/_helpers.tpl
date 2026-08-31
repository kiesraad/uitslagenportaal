{{/*
Every container running Django code reads the same three sources: the shared
config, the database credentials and the application secrets.
*/}}
{{- define "uitslagenportaal.envFrom" -}}
- configMapRef:
    name: {{ .Release.Name }}-config
- secretRef:
    name: {{ .Values.db.credentialsSecret }}
- secretRef:
    name: {{ .Values.secrets.app }}
{{- end }}

{{/*
DB_SSLMODE is verify-ca against the managed database, so libpq needs the CA at
PGSSLROOTCERT. Both halves collapse to nothing when no CA secret is configured.
*/}}
{{- define "uitslagenportaal.dbCaMount" -}}
{{- if .Values.db.caSecret }}
volumeMounts:
  - name: db-ca
    mountPath: /etc/ssl/rdb
    readOnly: true
{{- end }}
{{- end }}

{{- define "uitslagenportaal.dbCaVolume" -}}
{{- if .Values.db.caSecret }}
volumes:
  - name: db-ca
    secret:
      secretName: {{ .Values.db.caSecret }}
{{- end }}
{{- end }}

{{/*
Holds a pod until the migration job has finished. --check applies nothing, and
fails while the database is still unreachable too, which is the same "not ready
yet" answer. Deliberately the backend image, celery included: the question is
whether the migration job has caught up, and that job runs the backend image.
*/}}
{{- define "uitslagenportaal.waitForMigrations" -}}
- name: wait-for-migrations
  image: {{ .Values.backend.image }}
  imagePullPolicy: {{ .Values.backend.pullPolicy }}
  command:
    - sh
    - -c
    - |
      until python manage.py migrate --check; do
        echo "waiting for migrations"
        sleep 5
      done
  envFrom:
    {{- include "uitslagenportaal.envFrom" . | nindent 4 }}
  {{- include "uitslagenportaal.dbCaMount" . | nindent 2 }}
{{- end }}
