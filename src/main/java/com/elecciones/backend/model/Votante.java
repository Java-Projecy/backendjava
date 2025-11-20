package com.elecciones.backend.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import lombok.Builder;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "votantes")
@Getter
@Setter
public class Votante {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(unique = true, nullable = false, length = 8)
    private String dni;

    @Column(nullable = false)
    private String nombres;

    @Column(name = "apellido_paterno", nullable = false)
    private String apellido_paterno;

    @Column(name = "apellido_materno", nullable = false)
    private String apellido_materno;

    // Columna generada en la DB → no se inserta ni actualiza desde Java
    @Column(name = "nombre_completo", insertable = false, updatable = false)
    private String nombre_completo;

    private LocalDate fecha_nacimiento;
    private Integer edad;

    @Column(nullable = false)
    private String departamento;
    private String provincia;
    private String distrito;

    private String direccion;
    private String direccion_completa;
    private String ubigeo_reniec;
    private String ubigeo_sunat;
    private String telefono;
    private String email;

    @Column(nullable = false)
    private String estado = "Activo";

    @Builder.Default
    @Column(name = "created_at", nullable = false)
    private LocalDateTime created_at = LocalDateTime.now();

    @Builder.Default
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updated_at = LocalDateTime.now();

    @PrePersist
    protected void onCreate() {
        created_at = LocalDateTime.now();
        updated_at = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updated_at = LocalDateTime.now();
    }
}