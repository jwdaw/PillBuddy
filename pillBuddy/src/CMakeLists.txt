set(COMPONENT_SRCS "subscribe_publish_sample.c")
set(COMPONENT_ADD_INCLUDEDIRS ".")


register_component()

if(CONFIG_EXAMPLE_EMBEDDED_CERTS)
target_add_binary_data(${COMPONENT_TARGET} "certs/aws-root-ca.pem" TEXT)
target_add_binary_data(${COMPONENT_TARGET} "certs/pillBuddy.cert.pem" TEXT)
target_add_binary_data(${COMPONENT_TARGET} "certs/pillBuddy.private.key" TEXT)
endif()
