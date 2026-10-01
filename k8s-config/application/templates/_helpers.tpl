{{/* Common backend envFrom */}}
{{- define "uitslagenportaal.backendEnvFrom" -}}
- configMapRef:
    name: {{ .Release.Name }}-config
- secretRef:
    name: {{ .Values.db.credSecret }}
- secretRef:
    name: {{ .Values.redis.credSecret }}
- secretRef:
    name: {{ .Values.objectStorage.credSecret }}
- secretRef:
    name: {{ .Values.backend.appSecret }}
- secretRef:
    name: {{ .Values.backend.importerSecret }}
{{- end }}

{{/* Both CAs are read from a file and used to verify the DB and Redis connections. */}}
{{- define "uitslagenportaal.caVolumeMounts" -}}
volumeMounts:
  - name: db-ca
    mountPath: /etc/ssl/rdb
    readOnly: true
  - name: redis-ca
    mountPath: /etc/ssl/redis
    readOnly: true
{{- end }}

{{- define "uitslagenportaal.caVolumes" -}}
volumes:
  - name: db-ca
    secret:
      secretName: {{ .Values.db.credSecret }}
      optional: true
      items:
        - key: DB_CA_CERT
          path: ca.pem
  - name: redis-ca
    secret:
      secretName: {{ .Values.redis.credSecret }}
      optional: true
      items:
        - key: REDIS_CA_CERT
          path: ca.pem
{{- end }}

{{/*
Holds a pod until the migration job has finished. --check applies nothing, and
fails while the database is still unreachable or not fully migrated.
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
        echo "waiting for migrations..."
        sleep 5
      done
      echo "Migrations applied"
  envFrom:
    {{- include "uitslagenportaal.backendEnvFrom" . | nindent 4 }}
  {{- include "uitslagenportaal.caVolumeMounts" . | nindent 2 }}
{{- end }}
