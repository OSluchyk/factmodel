# nested-field

A STRUCT (`context`) and an ARRAY (`tags`) field. The anchor reference and a join use the nested path `context.user_id`. Rendering that join per SQL dialect is deferred.

Plan case: `nested-field`. Gate: pass.
