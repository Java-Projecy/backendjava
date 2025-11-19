package com.elecciones.backend.model;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "candidatos")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Candidato {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(nullable = false)
    private String nombre;

    @Column(nullable = false)
    private String partido;

    @Column(name = "tipo_eleccion", nullable = false)
    private String tipoEleccion;

    private String descripcion;
    private String imageUrl;

    @Column(columnDefinition = "jsonb")
    private String propuestas;

    private String experiencia;
    private String educacion;

    @Builder.Default
    private Boolean isActive = true;

    @Builder.Default
    private LocalDateTime created_at = LocalDateTime.now();

    @Builder.Default
    private LocalDateTime updated_at = LocalDateTime.now();
}
