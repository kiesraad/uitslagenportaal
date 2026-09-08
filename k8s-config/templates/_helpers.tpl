{{/* Common backend envFrom */}}
{{- define "uitslagenportaal.backendEnvFrom" -}}
- configMapRef:
    name: {{ .Release.Name }}-config
- secretRef:
    name: {{ .Values.db.credSecret }}
- secretRef:
    name: {{ .Values.redis.credSecret }}
- secretRef:
    name: {{ .Values.backend.appSecret }}
- secretRef:
    name: {{ .Values.backend.importerSecret }}
{{- end }}

{{/*
libpq reads the CA from a file at PGSSLROOTCERT, but the same secret is also
consumed with envFrom: hence the env-var-safe key DB_CA_CERT, renamed on the way in.
Without DB_CA_CERT the mount stays empty, which only the verify-* sslmodes mind.
*/}}
{{- define "uitslagenportaal.dbCaMount" -}}
volumeMounts:
  - name: db-ca
    mountPath: /etc/ssl/rdb
    readOnly: true
{{- end }}

{{- define "uitslagenportaal.dbCaVolume" -}}
volumes:
  - name: db-ca
    secret:
      secretName: {{ .Values.db.credSecret }}
      optional: true
      items:
        - key: DB_CA_CERT
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
  {{- include "uitslagenportaal.dbCaMount" . | nindent 2 }}
{{- end }}
