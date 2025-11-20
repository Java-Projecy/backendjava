package com.elecciones.backend.model;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "votantes")
@Getter @Setter
public class Votante {

    @Id @GeneratedValue
    private UUID id;

    @Column(unique = true, nullable = false, length = 8)
    private String dni;

    @Column(nullable = false)
    private String nombres;

    @Column(name = "apellido_paterno", nullable = false)
    private String apellido_paterno;

    @Column(name = "apellido_materno", nullable = false)
    private String apellido_materno;

    // Columna generada automáticamente en la DB
    @Column(name = "nombre_completo", insertable = false, updatable = false)
    private String nombre_completo;

    @Column(nullable = false)
    private String departamento;
    
    @Column(nullable = false)
    private String provincia;
    
    @Column(nullable = false)
    private String distrito;

    private String direccion;
    private String direccion_completa;
    private String ubigeo_reniec;
    private String ubigeo_sunat;
    private String telefono;
    private String email;

    @Column(nullable = false, columnDefinition = "varchar(20) default 'Activo'")
    private String estado = "Activo";

    // ¡¡ESTO ES LO QUE ARREGLA EL 500!!
    @Column(name = "created_at", insertable = false, updatable = false)
    @CreationTimestamp
    private LocalDateTime created_at;

    @Column(name = "updated_at", insertable = false, updatable = false)
    @UpdateTimestamp
    private LocalDateTime updated_at;
}